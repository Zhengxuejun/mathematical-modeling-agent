from __future__ import annotations

import hashlib
import json
import shutil
import subprocess
import sys
from pathlib import Path

import pytest

from scripts.candidate_tree.contracts import TreeError, validate_tree
from scripts.candidate_tree.service import add_candidate, evaluate_candidate, get_tree, initialize_tree, select_candidate

ROOT = Path(__file__).resolve().parents[2]


def make_candidate(
    project: Path,
    name: str,
    *,
    objective: float = 10,
    validation: float = .8,
    feasible: bool = True,
    validation_passed: bool = True,
    exit_code: int = 0,
    runtime: float = 1,
) -> Path:
    candidate = project / "08_candidates" / name
    artifacts = candidate / "artifacts"
    artifacts.mkdir(parents=True)
    result = b"result\nverified\n"
    digest = hashlib.sha256(result).hexdigest()
    (artifacts / "results.csv").write_bytes(result)
    inputs = project / "01_inputs"
    inputs.mkdir(exist_ok=True)
    input_path = inputs / "data.csv"
    if not input_path.exists():
        input_path.write_bytes(b"x,y\n1,2\n")
    input_digest = hashlib.sha256(input_path.read_bytes()).hexdigest()
    solution = {
        "model_name": name,
        "model_version": "1",
        "random_seed": 20260712,
        "metrics": {"objective": objective, "validation_score": validation},
        "checks": {"feasible": feasible, "validation_passed": validation_passed},
        "evidence": {"results": "artifacts/results.csv"},
    }
    run_record = {
        "command": f"touch {project / 'EXECUTED'}",
        "runtime_seconds": runtime,
        "exit_code": exit_code,
        "input_hashes": {"01_inputs/data.csv": input_digest},
        "artifacts": {"artifacts/results.csv": digest},
    }
    (candidate / "solution.json").write_text(json.dumps(solution), encoding="utf-8")
    (candidate / "run_record.json").write_text(json.dumps(run_record), encoding="utf-8")
    (candidate / "report.md").write_text(f"# {name}\n", encoding="utf-8")
    return candidate


def init_project(tmp_path: Path, **kwargs: object) -> Path:
    project = tmp_path / "project"
    project.mkdir()
    initialize_tree(project, "objective", "maximize", "validation_score", **kwargs)
    return project


def test_bounded_lineage_stable_ids_and_safe_paths(tmp_path: Path) -> None:
    project = init_project(tmp_path, max_candidates=3, max_depth=1)
    first_path = make_candidate(project, "baseline")
    second_path = make_candidate(project, "child")
    third_path = make_candidate(project, "too-deep")
    first = add_candidate(project, "08_candidates/baseline", "baseline", "establish baseline")
    second = add_candidate(project, "08_candidates/child", "child", "improve validation", first["candidate_id"])
    assert first["candidate_id"] == "C001"
    assert second["candidate_id"] == "C002"
    assert second["depth"] == 1
    with pytest.raises(TreeError, match="depth limit"):
        add_candidate(project, "08_candidates/too-deep", "deep", "too deep", second["candidate_id"])
    with pytest.raises(TreeError, match="already registered"):
        add_candidate(project, "08_candidates/baseline", "duplicate", "duplicate")
    outside = tmp_path / "outside"
    outside.mkdir()
    (project / "08_candidates/link").symlink_to(outside)
    with pytest.raises(TreeError, match="escapes project"):
        add_candidate(project, "08_candidates/link", "escape", "unsafe")
    assert first_path.is_dir() and second_path.is_dir() and third_path.is_dir()


def test_candidate_count_limit_is_enforced(tmp_path: Path) -> None:
    project = init_project(tmp_path, max_candidates=1)
    make_candidate(project, "first")
    make_candidate(project, "second")
    add_candidate(project, "08_candidates/first", "first", "first branch")
    with pytest.raises(TreeError, match="candidate limit reached"):
        add_candidate(project, "08_candidates/second", "second", "second branch")


@pytest.mark.parametrize(
    ("changes", "reason"),
    [
        ({"exit_code": 2}, "run succeeded"),
        ({"feasible": False}, "feasible gate"),
        ({"validation_passed": False}, "validation passed"),
    ],
)
def test_evaluation_blocks_failed_gates_and_never_executes_command(tmp_path: Path, changes: dict[str, object], reason: str) -> None:
    project = init_project(tmp_path)
    candidate = make_candidate(project, "candidate")
    if "exit_code" in changes:
        path = candidate / "run_record.json"
        value = json.loads(path.read_text())
        value["exit_code"] = changes["exit_code"]
    else:
        path = candidate / "solution.json"
        value = json.loads(path.read_text())
        value["checks"].update(changes)
    path.write_text(json.dumps(value))
    node = add_candidate(project, "08_candidates/candidate", "candidate", "test a gate")
    evaluated = evaluate_candidate(project, node["candidate_id"])
    assert evaluated["status"] == "blocked"
    assert any(reason in item for item in evaluated["evaluation"]["blocking_reasons"])
    assert not (project / "EXECUTED").exists()


def test_evaluation_verifies_evidence_and_preserves_readiness_files(tmp_path: Path) -> None:
    project = init_project(tmp_path)
    make_candidate(project, "good")
    readiness = project / "06_过程记录/competition_readiness.json"
    readiness.parent.mkdir(parents=True, exist_ok=True)
    readiness.write_text('{"competition_ready": false}\n')
    before = readiness.read_bytes()
    node = add_candidate(project, "08_candidates/good", "good", "valid evidence")
    evaluated = evaluate_candidate(project, node["candidate_id"])
    assert evaluated["status"] == "evaluated"
    assert evaluated["evaluation"]["eligible"] is True
    assert evaluated["evaluation"]["gates"] == {
        "contract_valid": True,
        "run_succeeded": True,
        "inputs_verified": True,
        "feasible": True,
        "validation_passed": True,
        "evidence_verified": True,
        "snapshot_current": True,
    }
    assert readiness.read_bytes() == before
    assert not (project / "EXECUTED").exists()
    report = project / "06_过程记录/候选方案树/candidate_tree.md"
    assert "does not imply paper_ready" in report.read_text(encoding="utf-8")


def test_hash_mismatch_blocks_candidate(tmp_path: Path) -> None:
    project = init_project(tmp_path)
    candidate = make_candidate(project, "tampered")
    (candidate / "artifacts/results.csv").write_text("changed")
    node = add_candidate(project, "08_candidates/tampered", "tampered", "bad hash")
    evaluated = evaluate_candidate(project, node["candidate_id"])
    assert evaluated["status"] == "blocked"
    assert "evidence hash mismatch" in evaluated["evaluation"]["blocking_reasons"][0]


def test_input_hash_mismatch_and_non_finite_metric_block_candidates(tmp_path: Path) -> None:
    project = init_project(tmp_path)
    first_path = make_candidate(project, "input-tampered")
    first = add_candidate(project, "08_candidates/input-tampered", "input", "tampered input")
    (project / "01_inputs/data.csv").write_text("changed")
    evaluated = evaluate_candidate(project, first["candidate_id"])
    assert evaluated["status"] == "blocked"
    assert "input hash mismatch" in evaluated["evaluation"]["blocking_reasons"][0]

    (project / "01_inputs/data.csv").write_bytes(b"x,y\n1,2\n")
    second_path = make_candidate(project, "non-finite")
    solution_path = second_path / "solution.json"
    solution = json.loads(solution_path.read_text())
    solution["metrics"]["objective"] = float("nan")
    solution_path.write_text(json.dumps(solution))
    second = add_candidate(project, "08_candidates/non-finite", "nan", "invalid metric")
    evaluated = evaluate_candidate(project, second["candidate_id"])
    assert evaluated["status"] == "blocked"
    assert "cannot read valid JSON" in evaluated["evaluation"]["blocking_reasons"][0]
    assert first_path.is_dir()


def test_tree_contract_rejects_status_evaluation_drift(tmp_path: Path) -> None:
    project = init_project(tmp_path)
    make_candidate(project, "good")
    node = add_candidate(project, "08_candidates/good", "good", "valid candidate")
    evaluate_candidate(project, node["candidate_id"])
    tree = get_tree(project)
    tree["nodes"][0]["status"] = "blocked"
    with pytest.raises(TreeError, match="blocked status is inconsistent"):
        validate_tree(tree)


def test_selection_is_deterministic_and_can_reselect(tmp_path: Path) -> None:
    project = init_project(tmp_path)
    first_path = make_candidate(project, "first", objective=10, validation=.8, runtime=.5)
    make_candidate(project, "second", objective=8, validation=.9, runtime=1)
    first = add_candidate(project, "08_candidates/first", "first", "higher objective")
    second = add_candidate(project, "08_candidates/second", "second", "higher validation", first["candidate_id"])
    evaluate_candidate(project, first["candidate_id"])
    evaluate_candidate(project, second["candidate_id"])
    assert select_candidate(project)["candidate_id"] == "C002"
    solution_path = first_path / "solution.json"
    solution = json.loads(solution_path.read_text())
    solution["metrics"]["validation_score"] = .95
    solution_path.write_text(json.dumps(solution))
    evaluate_candidate(project, first["candidate_id"])
    assert select_candidate(project)["candidate_id"] == "C001"
    tree = get_tree(project)
    assert [item["candidate_id"] for item in tree["selection_ranking"]] == ["C001", "C002"]
    assert next(node for node in tree["nodes"] if node["candidate_id"] == "C002")["status"] == "evaluated"


def test_selection_rejects_different_input_snapshots(tmp_path: Path) -> None:
    project = init_project(tmp_path)
    make_candidate(project, "first")
    second_path = make_candidate(project, "second")
    alternate = project / "01_inputs/alternate.csv"
    alternate.write_bytes(b"x,y\n2,3\n")
    run_path = second_path / "run_record.json"
    run = json.loads(run_path.read_text())
    run["input_hashes"] = {"01_inputs/alternate.csv": hashlib.sha256(alternate.read_bytes()).hexdigest()}
    run_path.write_text(json.dumps(run))
    first = add_candidate(project, "08_candidates/first", "first", "first input")
    second = add_candidate(project, "08_candidates/second", "second", "second input")
    evaluate_candidate(project, first["candidate_id"])
    evaluate_candidate(project, second["candidate_id"])
    with pytest.raises(TreeError, match="incomparable input provenance"):
        select_candidate(project)


def test_selection_blocks_stale_evaluation_snapshot(tmp_path: Path) -> None:
    project = init_project(tmp_path)
    candidate = make_candidate(project, "stale")
    node = add_candidate(project, "08_candidates/stale", "stale", "evaluate then mutate")
    evaluate_candidate(project, node["candidate_id"])
    (candidate / "report.md").write_text("changed after evaluation")
    with pytest.raises(TreeError, match="no eligible"):
        select_candidate(project)
    stored = get_tree(project)["nodes"][0]
    assert stored["status"] == "blocked"
    assert stored["evaluation"]["gates"]["snapshot_current"] is False
    assert "candidate artifacts changed after evaluation" in stored["evaluation"]["blocking_reasons"]


def test_mixed_benchmark_coverage_blocks_selection(tmp_path: Path) -> None:
    project = init_project(tmp_path)
    source = ROOT / "benchmarks/fixtures/optimization_capacity/good"
    benchmark_candidate = project / "08_candidates/benchmark"
    shutil.copytree(source, benchmark_candidate)
    case_input = ROOT / "benchmarks/cases/optimization_capacity/input/data.csv"
    project_input = project / "input/data.csv"
    project_input.parent.mkdir(parents=True)
    shutil.copy2(case_input, project_input)
    solution_path = benchmark_candidate / "solution.json"
    solution = json.loads(solution_path.read_text())
    solution["metrics"]["validation_score"] = .9
    solution["checks"].update({"feasible": True, "validation_passed": True})
    solution_path.write_text(json.dumps(solution))
    generic_candidate = make_candidate(project, "generic", validation=.95)
    generic_run_path = generic_candidate / "run_record.json"
    generic_run = json.loads(generic_run_path.read_text())
    generic_run["input_hashes"] = {
        "input/data.csv": hashlib.sha256(project_input.read_bytes()).hexdigest()
    }
    generic_run_path.write_text(json.dumps(generic_run))
    first = add_candidate(project, "08_candidates/benchmark", "benchmark", "benchmark branch")
    second = add_candidate(project, "08_candidates/generic", "generic", "generic branch")
    benchmark_case = ROOT / "benchmarks/cases/optimization_capacity"
    evaluated = evaluate_candidate(project, first["candidate_id"], benchmark_case)
    assert evaluated["evaluation"]["benchmark"]["verdict"] == "strong"
    evaluate_candidate(project, second["candidate_id"])
    with pytest.raises(TreeError, match="mixed or incomparable"):
        select_candidate(project)


def test_blocked_benchmark_verdict_blocks_tree_node(tmp_path: Path) -> None:
    project = init_project(tmp_path)
    source = ROOT / "benchmarks/fixtures/optimization_capacity/bad"
    candidate = project / "08_candidates/blocked"
    shutil.copytree(source, candidate)
    case_input = ROOT / "benchmarks/cases/optimization_capacity/input/data.csv"
    project_input = project / "input/data.csv"
    project_input.parent.mkdir(parents=True)
    shutil.copy2(case_input, project_input)
    solution_path = candidate / "solution.json"
    solution = json.loads(solution_path.read_text())
    solution["metrics"]["validation_score"] = .9
    solution["checks"].update({"feasible": True, "validation_passed": True})
    solution_path.write_text(json.dumps(solution))
    node = add_candidate(project, "08_candidates/blocked", "blocked", "infeasible benchmark")
    evaluated = evaluate_candidate(project, node["candidate_id"], ROOT / "benchmarks/cases/optimization_capacity")
    assert evaluated["status"] == "blocked"
    assert evaluated["evaluation"]["benchmark"]["verdict"] == "blocked"
    assert "Benchmark verdict is blocked" in evaluated["evaluation"]["blocking_reasons"]


def test_cli_smoke(tmp_path: Path) -> None:
    project = tmp_path / "project"
    project.mkdir()
    make_candidate(project, "baseline")
    script = ROOT / "scripts/candidate_solution_tree.py"
    commands = [
        ["init", str(project), "--objective-metric", "objective", "--direction", "maximize"],
        ["add", str(project), "--submission", "08_candidates/baseline", "--label", "baseline", "--hypothesis", "baseline"],
        ["evaluate", str(project), "--candidate", "C001"],
        ["select", str(project)],
        ["status", str(project), "--json"],
    ]
    for command in commands:
        result = subprocess.run([sys.executable, str(script), *command], text=True, capture_output=True)
        assert result.returncode == 0, result.stdout + result.stderr
    assert '"selected_candidate_id": "C001"' in result.stdout
    assert not (project / "EXECUTED").exists()
