from __future__ import annotations

import csv
import subprocess
import sys
import threading
import time
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

import pytest

SCRIPT_DIR = Path(__file__).resolve().parents[1]
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))

import contest_qc_gate
from contest_qc_gate import (
    ArtifactFreezeError,
    MODEL_HANDOFF_TEMPLATE,
    QC_REL,
    REGISTRY_HEADERS,
    evaluate,
    freeze_run_artifacts,
    init_project,
    non_template,
    path_exists_from_project,
)


def write_rows(path: Path, rows: list[dict[str, str]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8-sig", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=REGISTRY_HEADERS[path.name])
        writer.writeheader()
        writer.writerows(rows)


def read_rows(path: Path) -> list[dict[str, str]]:
    with path.open("r", encoding="utf-8-sig", newline="") as handle:
        return [dict(row) for row in csv.DictReader(handle)]


def make_final_ready_fixture(project: Path, *, freeze_artifacts: bool = True) -> None:
    (project / "01_原始数据").mkdir(parents=True)
    (project / "01_原始数据" / "input.csv").write_text("id,value\na,1\n", encoding="utf-8")
    (project / "02_代码").mkdir()
    (project / "02_代码" / "solve.py").write_text("print('fixture solve')\n", encoding="utf-8")
    (project / "03_结果表格").mkdir()
    (project / "03_结果表格" / "result.csv").write_text("metric,value\nobjective,1\n", encoding="utf-8")
    analysis = project / "06_过程记录" / "problem_analysis.md"
    analysis.parent.mkdir(parents=True)
    analysis.write_text(
        "# 题目解析\n\n"
        "## 小问一\n在给定真实附件上确定满足容量约束的最小成本方案。\n\n"
        "## 数据清单\ninput.csv 包含实体 id 与价值 value，单位为万元。\n\n"
        "## 输出要求\n输出可行方案、总成本、约束残差和敏感性结论。\n\n"
        "## 题型路由\n这是一个有显式容量约束的离散优化问题，需与 baseline 比较。\n",
        encoding="utf-8",
    )
    init_project(project)
    qc = project / QC_REL
    (qc / "model_handoff.md").write_text(
        "# 模型交接\n\n"
        "## 当前锁定\n小问一；交付物 D1；模型版本 v1。\n\n"
        "## 模型路线与选择理由\n采用最小成本整数规划，并以贪心方案为 baseline。\n\n"
        "## 变量、单位与定义\nx_i 为是否选择实体，单位为 1；c_i 为成本，单位为万元。\n\n"
        "## 目标与约束\n最小化总成本，且容量、唯一性和非负约束必须满足。\n\n"
        "## 输入与输出\n输入为 01_原始数据/input.csv；输出为结果表与约束检查表。\n\n"
        "## PoC 与可复现运行\nPoC P1 在真实 input.csv 的首行上运行；正式运行 R1 固定 seed。\n\n"
        "## 验证与稳健性\n验证量纲、边界、容量残差，并比较 baseline。\n\n"
        "## 待解决缺口\n无。\n",
        encoding="utf-8",
    )
    write_rows(qc / "deliverable_matrix.csv", [{
        "deliverable_id": "D1", "problem_id": "fixture", "subquestion": "Q1",
        "required_output": "最小成本可行方案", "format": "csv", "evidence_needed": "R1",
        "owner": "model", "status": "provided", "risk_note": "",
    }])
    write_rows(qc / "poc_registry.csv", [{
        "poc_id": "P1", "problem_id": "fixture", "subquestion": "Q1", "candidate_id": "main",
        "model_version": "v1", "script_or_command": "python solve.py --slice 1",
        "source_data": "01_原始数据/input.csv", "source_slice": "row=1", "metric": "objective",
        "value": "1", "unit": "万元", "runtime": "0.01", "status": "passed",
        "failure_reason": "", "promoted_model_version": "v1", "notes": "",
    }])
    write_rows(qc / "math_verification.csv", [{
        "check_id": "V1", "subquestion": "Q1", "artifact": "model", "location": "constraint 1",
        "claim_id": "C1", "check_type": "constraint", "input_ref": "input.csv",
        "expected_relation": "residual <= 0", "observed": "0", "status": "passed",
        "severity": "P1", "minimum_fix": "", "owner": "model",
    }])
    write_rows(qc / "run_record.csv", [{
        "run_id": "R1", "problem_id": "fixture", "model_version": "v1", "command": "python solve.py",
        "entry_script": "02_代码/solve.py", "input_files": "01_原始数据/input.csv", "parameters": "capacity=1",
        "seed": "0", "solver": "scipy", "solver_status": "optimal", "warnings": "",
        "output_tables": "03_结果表格/result.csv", "output_figures": "04_图表/result.png", "log_path": "",
        "started_at": "2026-01-01", "completed_at": "2026-01-01", "run_status": "completed",
        "superseded_by": "", "notes": "",
    }])
    write_rows(qc / "result_registry.csv", [{
        "result_id": "RSLT1", "deliverable_id": "D1", "problem_id": "fixture", "scenario_id": "base", "metric": "objective",
        "value": "1", "unit": "万元", "comparison_or_baseline": "greedy", "source_table": "03_结果表格/result.csv",
        "source_figure": "", "source_script": "02_代码/solve.py", "run_id": "R1",
        "validation_status": "paper_ready", "frozen_at": "2026-01-01", "superseded_by": "", "notes": "",
    }])
    figure = project / "04_图表" / "result.png"
    figure.parent.mkdir(parents=True)
    figure.write_bytes(b"fixture")
    write_rows(qc / "figure_evidence.csv", [{
        "figure_id": "F1", "deliverable_id": "D1", "claim_id": "C1", "figure_path": "04_图表/result.png", "run_id": "R1",
        "caption": "结果", "post_figure_conclusion": "目标值为 1", "risk_note": "",
        "render_check_status": "passed", "human_visual_check": "", "visual_check_note": "fixture",
        "validation_status": "paper_ready",
    }])
    write_rows(qc / "claim_ledger.csv", [{
        "claim_id": "C1", "location": "conclusion", "claim_text": "目标值为 1", "metric": "objective",
        "value": "1", "unit": "万元", "scenario": "base", "evidence_id": "RSLT1",
        "evidence_type": "result", "body_location": "5.1", "status": "paper_ready", "risk_note": "",
    }])
    write_rows(qc / "review_findings.csv", [])
    write_rows(qc / "review_pass_items.csv", [{
        "pass_item_id": f"P{i}", "source_module": "review", "claim_id": "C1", "file": "report.md",
        "location": f"line {i}", "value": "1", "constraint_direction": "<=", "expected": "1",
        "observed": "1", "evidence_ref": "RSLT1", "status": "passed", "notes": "",
    } for i in range(1, 6)])
    (qc / "submission_checklist.md").write_text(
        "official_rule_source: https://example.org/rules\n"
        "rule_checked_at: 2026-01-01\n"
        "anonymity_check: passed\n"
        "reproducibility: passed\n"
        "ai_disclosure_status: not_required\n",
        encoding="utf-8",
    )
    if freeze_artifacts:
        freeze_run_artifacts(project, "R1")


def test_init_creates_qc_registry_headers_and_early_gate_blocks_empty_project(tmp_path: Path) -> None:
    project = tmp_path / "project"
    project.mkdir()
    init_project(project)
    qc = project / QC_REL
    assert (qc / "deliverable_matrix.csv").exists()
    assert (qc / "artifact_manifest.csv").exists()
    assert (qc / "model_handoff.md").exists()
    summary = evaluate(project, "early")
    assert summary["readiness"] == "blocked"
    assert any(check["id"] == "deliverable_matrix" and check["status"] == "fail" for check in summary["checks"])


def test_untouched_model_handoff_template_is_not_substantive() -> None:
    assert not non_template(MODEL_HANDOFF_TEMPLATE, minimum=240)


def test_evidence_path_must_resolve_inside_project(tmp_path: Path) -> None:
    project = tmp_path / "project"
    project.mkdir()
    inside = project / "input.csv"
    inside.write_text("id,value\na,1\n", encoding="utf-8")
    outside = tmp_path / "outside.csv"
    outside.write_text("id,value\nb,2\n", encoding="utf-8")
    escaping_link = project / "external.csv"
    escaping_link.symlink_to(outside)

    assert path_exists_from_project(project, "input.csv")
    assert not path_exists_from_project(project, str(outside))
    assert not path_exists_from_project(project, "../outside.csv")
    assert not path_exists_from_project(project, "external.csv")


def test_final_gate_requires_evidence_and_blocks_open_p1(tmp_path: Path) -> None:
    project = tmp_path / "project"
    project.mkdir()
    make_final_ready_fixture(project)
    early = evaluate(project, "early")
    assert early["readiness"] == "early_ready"
    summary = evaluate(project, "final")
    assert summary["readiness"] == "final_ready"

    (project / "02_代码" / "solve.py").unlink()
    broken_reference = evaluate(project, "model")
    assert broken_reference["readiness"] == "blocked"
    assert any(check["id"] == "reproducible_run" and check["status"] == "fail" for check in broken_reference["checks"])
    (project / "02_代码" / "solve.py").write_text("print('fixture solve')\n", encoding="utf-8")

    qc = project / QC_REL
    write_rows(qc / "review_findings.csv", [{
        "finding_id": "F1", "severity": "P1", "dimension": "evidence", "score_risk": "major",
        "artifact": "claim_ledger.csv", "location": "C1", "issue": "missing check", "impact": "claim blocked",
        "minimum_fix": "add verification", "owner": "model", "status": "open",
    }])
    blocked = evaluate(project, "final")
    assert blocked["readiness"] == "blocked"
    assert any(check["id"] == "judge_risk" and check["status"] == "fail" for check in blocked["checks"])


@pytest.mark.parametrize(
    ("mutation", "issue_marker"),
    [
        ("empty_result_id", "result_id:empty=1"),
        ("duplicate_result_id", "result_id:duplicate=RSLT1"),
        ("unqualified_result", "result_id:unqualified=1"),
        ("empty_figure_id", "figure_id:empty=1"),
        ("duplicate_figure_id", "figure_id:duplicate=F1"),
        ("unqualified_figure", "figure_id:unqualified=1"),
        ("empty_claim_id", "claim_id:empty=1"),
        ("duplicate_claim_id", "claim_id:duplicate=C1"),
        ("evidence_type_mismatch", "C1:unknown_figure:RSLT1"),
    ],
)
def test_final_gate_rejects_invalid_paper_evidence_identities(
    tmp_path: Path, mutation: str, issue_marker: str,
) -> None:
    project = tmp_path / "project"
    project.mkdir()
    make_final_ready_fixture(project)
    qc = project / QC_REL
    results = read_rows(qc / "result_registry.csv")
    figures = read_rows(qc / "figure_evidence.csv")
    claims = read_rows(qc / "claim_ledger.csv")

    if mutation == "empty_result_id":
        results.append({**results[0], "result_id": "", "scenario_id": "empty"})
    elif mutation == "duplicate_result_id":
        results.append({**results[0], "scenario_id": "stress", "value": "2"})
    elif mutation == "unqualified_result":
        results.append({
            **results[0],
            "result_id": "BROKEN-R",
            "run_id": "MISSING",
            "source_table": "03_结果表格/missing.csv",
        })
    elif mutation == "empty_figure_id":
        figures.append({**figures[0], "figure_id": "", "caption": "空身份图"})
    elif mutation == "duplicate_figure_id":
        figures.append({**figures[0], "caption": "重复身份图"})
    elif mutation == "unqualified_figure":
        figures.append({
            **figures[0],
            "figure_id": "BROKEN-F",
            "run_id": "MISSING",
            "figure_path": "04_图表/missing.png",
        })
    elif mutation == "empty_claim_id":
        claims[0]["claim_id"] = ""
    elif mutation == "duplicate_claim_id":
        claims.append({**claims[0], "claim_text": "重复身份主张"})
    else:
        claims[0]["evidence_type"] = "figure"

    write_rows(qc / "result_registry.csv", results)
    write_rows(qc / "figure_evidence.csv", figures)
    write_rows(qc / "claim_ledger.csv", claims)

    summary = evaluate(project, "final")

    assert summary["readiness"] == "blocked"
    evidence = next(check for check in summary["checks"] if check["id"] == "paper_claim_evidence")
    assert evidence["status"] == "fail"
    assert issue_marker in evidence["evidence"]


def test_final_gate_accepts_typed_figure_evidence_identity(tmp_path: Path) -> None:
    project = tmp_path / "project"
    project.mkdir()
    make_final_ready_fixture(project)
    qc = project / QC_REL
    claims = read_rows(qc / "claim_ledger.csv")
    claims[0]["evidence_id"] = "F1"
    claims[0]["evidence_type"] = "figure"
    write_rows(qc / "claim_ledger.csv", claims)

    summary = evaluate(project, "final")

    assert summary["readiness"] == "final_ready"
    evidence = next(check for check in summary["checks"] if check["id"] == "paper_claim_evidence")
    assert evidence["status"] == "pass"


def test_final_gate_fails_closed_until_supporting_run_is_frozen(tmp_path: Path) -> None:
    project = tmp_path / "project"
    project.mkdir()
    make_final_ready_fixture(project, freeze_artifacts=False)

    summary = evaluate(project, "final")

    assert summary["readiness"] == "blocked"
    integrity = next(check for check in summary["checks"] if check["id"] == "artifact_integrity")
    assert integrity["status"] == "fail"
    assert "R1" in integrity["evidence"]


@pytest.mark.parametrize(
    "relative_path",
    [
        "01_原始数据/input.csv",
        "02_代码/solve.py",
        "03_结果表格/result.csv",
        "04_图表/result.png",
    ],
)
def test_final_gate_blocks_when_frozen_run_artifact_changes(tmp_path: Path, relative_path: str) -> None:
    project = tmp_path / "project"
    project.mkdir()
    make_final_ready_fixture(project)
    assert evaluate(project, "final")["readiness"] == "final_ready"

    artifact = project / relative_path
    artifact.write_bytes(artifact.read_bytes() + b"changed-after-freeze")

    summary = evaluate(project, "final")
    assert summary["readiness"] == "blocked"
    integrity = next(check for check in summary["checks"] if check["id"] == "artifact_integrity")
    assert integrity["status"] == "fail"
    assert "R1" in integrity["evidence"]
    assert relative_path in integrity["evidence"]


def test_freeze_run_is_idempotent_and_never_executes_recorded_command(tmp_path: Path) -> None:
    project = tmp_path / "project"
    project.mkdir()
    make_final_ready_fixture(project, freeze_artifacts=False)
    qc = project / QC_REL
    sentinel = project / "command-was-executed.txt"
    runs = read_rows(qc / "run_record.csv")
    runs[0]["command"] = f"python -c \"from pathlib import Path; Path({str(sentinel)!r}).write_text('bad')\""
    write_rows(qc / "run_record.csv", runs)

    first_rows = freeze_run_artifacts(project, "R1")
    first_bytes = (qc / "artifact_manifest.csv").read_bytes()
    second_rows = freeze_run_artifacts(project, "R1")
    second_bytes = (qc / "artifact_manifest.csv").read_bytes()

    assert first_rows == second_rows
    assert first_bytes == second_bytes
    assert not sentinel.exists()
    assert {row["role"] for row in first_rows} == {
        "entry_script", "input_file", "output_table", "output_figure",
    }


@pytest.mark.parametrize("bad_kind", ["parent", "absolute", "missing", "escaping_symlink"])
def test_freeze_rejects_unsafe_or_missing_paths_without_rewriting_manifest(tmp_path: Path, bad_kind: str) -> None:
    project = tmp_path / "project"
    project.mkdir()
    make_final_ready_fixture(project)
    qc = project / QC_REL
    before = (qc / "artifact_manifest.csv").read_bytes()
    outside = tmp_path / "outside.csv"
    outside.write_text("id,value\noutside,2\n", encoding="utf-8")
    if bad_kind == "parent":
        bad_path = "../outside.csv"
    elif bad_kind == "absolute":
        bad_path = str(project / "01_原始数据/input.csv")
    elif bad_kind == "missing":
        bad_path = "01_原始数据/missing.csv"
    else:
        link = project / "01_原始数据/outside-link.csv"
        link.symlink_to(outside)
        bad_path = "01_原始数据/outside-link.csv"
    runs = read_rows(qc / "run_record.csv")
    runs[0]["input_files"] = bad_path
    write_rows(qc / "run_record.csv", runs)

    with pytest.raises(ArtifactFreezeError):
        freeze_run_artifacts(project, "R1")

    assert (qc / "artifact_manifest.csv").read_bytes() == before
    reproducible = next(
        check for check in evaluate(project, "model")["checks"] if check["id"] == "reproducible_run"
    )
    assert reproducible["status"] == "fail"


@pytest.mark.parametrize("run_mutation", ["not_completed", "duplicate"])
def test_freeze_rejects_ambiguous_or_incomplete_run(tmp_path: Path, run_mutation: str) -> None:
    project = tmp_path / "project"
    project.mkdir()
    make_final_ready_fixture(project, freeze_artifacts=False)
    qc = project / QC_REL
    runs = read_rows(qc / "run_record.csv")
    if run_mutation == "not_completed":
        runs[0]["run_status"] = "failed"
    else:
        runs.append(dict(runs[0]))
    write_rows(qc / "run_record.csv", runs)
    before = (qc / "artifact_manifest.csv").read_bytes()

    with pytest.raises(ArtifactFreezeError):
        freeze_run_artifacts(project, "R1")

    assert (qc / "artifact_manifest.csv").read_bytes() == before


@pytest.mark.parametrize("missing_field", ["command", "input_files"])
def test_freeze_and_model_gate_reject_incomplete_reproduction_contract(tmp_path: Path, missing_field: str) -> None:
    project = tmp_path / "project"
    project.mkdir()
    make_final_ready_fixture(project, freeze_artifacts=False)
    qc = project / QC_REL
    runs = read_rows(qc / "run_record.csv")
    runs[0][missing_field] = ""
    write_rows(qc / "run_record.csv", runs)

    with pytest.raises(ArtifactFreezeError):
        freeze_run_artifacts(project, "R1")
    summary = evaluate(project, "model")
    assert summary["readiness"] == "blocked"
    reproducible = next(check for check in summary["checks"] if check["id"] == "reproducible_run")
    assert reproducible["status"] == "fail"


def test_explicit_no_external_input_declaration_can_be_frozen(tmp_path: Path) -> None:
    project = tmp_path / "project"
    project.mkdir()
    make_final_ready_fixture(project, freeze_artifacts=False)
    qc = project / QC_REL
    runs = read_rows(qc / "run_record.csv")
    runs[0]["input_files"] = "not_applicable"
    write_rows(qc / "run_record.csv", runs)

    rows = freeze_run_artifacts(project, "R1")

    assert "input_file" not in {row["role"] for row in rows}


def test_concurrent_freezes_preserve_both_runs(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    project = tmp_path / "project"
    project.mkdir()
    make_final_ready_fixture(project, freeze_artifacts=False)
    qc = project / QC_REL
    runs = read_rows(qc / "run_record.csv")
    runs.append({**runs[0], "run_id": "R2", "command": "python solve.py --repeat"})
    write_rows(qc / "run_record.csv", runs)
    write_rows(qc / "artifact_manifest.csv", [])
    original_fingerprint = contest_qc_gate.file_fingerprint

    def slow_fingerprint(path: Path) -> tuple[str, str]:
        time.sleep(0.02)
        return original_fingerprint(path)

    monkeypatch.setattr(contest_qc_gate, "file_fingerprint", slow_fingerprint)
    start = threading.Barrier(2)

    def freeze(run_id: str) -> None:
        start.wait(timeout=5)
        freeze_run_artifacts(project, run_id)

    with ThreadPoolExecutor(max_workers=2) as pool:
        futures = [pool.submit(freeze, run_id) for run_id in ("R1", "R2")]
        for future in futures:
            future.result(timeout=10)

    assert {row["run_id"] for row in read_rows(qc / "artifact_manifest.csv")} == {"R1", "R2"}


def test_atomic_replace_failure_preserves_existing_manifest(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    project = tmp_path / "project"
    project.mkdir()
    make_final_ready_fixture(project)
    qc = project / QC_REL
    before = (qc / "artifact_manifest.csv").read_bytes()
    (project / "03_结果表格/result.csv").write_text(
        "metric,value\nobjective,2\n", encoding="utf-8",
    )

    def fail_replace(source: str | Path, target: str | Path) -> None:
        raise OSError("injected replace failure")

    monkeypatch.setattr(contest_qc_gate.os, "replace", fail_replace)
    with pytest.raises(ArtifactFreezeError, match="atomically update"):
        freeze_run_artifacts(project, "R1")

    assert (qc / "artifact_manifest.csv").read_bytes() == before
    assert not list(qc.glob(".artifact_manifest.csv.*.tmp"))


def test_refreezing_one_run_preserves_other_run_records(tmp_path: Path) -> None:
    project = tmp_path / "project"
    project.mkdir()
    make_final_ready_fixture(project)
    qc = project / QC_REL
    runs = read_rows(qc / "run_record.csv")
    runs.append({**runs[0], "run_id": "R2", "command": "python solve.py --repeat"})
    write_rows(qc / "run_record.csv", runs)
    freeze_run_artifacts(project, "R2")
    r2_before = [row for row in read_rows(qc / "artifact_manifest.csv") if row["run_id"] == "R2"]

    (project / "03_结果表格/result.csv").write_text(
        "metric,value\nobjective,2\n", encoding="utf-8",
    )
    freeze_run_artifacts(project, "R1")

    r2_after = [row for row in read_rows(qc / "artifact_manifest.csv") if row["run_id"] == "R2"]
    assert r2_after == r2_before


def test_invalid_manifest_encoding_fails_closed_without_crashing(tmp_path: Path) -> None:
    project = tmp_path / "project"
    project.mkdir()
    make_final_ready_fixture(project)
    manifest = project / QC_REL / "artifact_manifest.csv"
    manifest.write_bytes(b"\xff\xfe\x00")

    summary = evaluate(project, "final")

    assert summary["readiness"] == "blocked"
    integrity = next(check for check in summary["checks"] if check["id"] == "artifact_integrity")
    assert integrity["status"] == "fail"
    assert "schema" in integrity["message"]


def test_paper_ready_source_script_may_be_a_frozen_run_dependency(tmp_path: Path) -> None:
    project = tmp_path / "project"
    project.mkdir()
    make_final_ready_fixture(project, freeze_artifacts=False)
    helper = project / "02_代码/model_core.py"
    helper.write_text("def solve():\n    return 1\n", encoding="utf-8")
    qc = project / QC_REL
    runs = read_rows(qc / "run_record.csv")
    runs[0]["input_files"] += ";02_代码/model_core.py"
    write_rows(qc / "run_record.csv", runs)
    results = read_rows(qc / "result_registry.csv")
    results[0]["source_script"] = "02_代码/model_core.py"
    write_rows(qc / "result_registry.csv", results)
    freeze_run_artifacts(project, "R1")

    assert evaluate(project, "final")["readiness"] == "final_ready"


def test_final_gate_rejects_paper_ready_table_not_declared_by_its_run(tmp_path: Path) -> None:
    project = tmp_path / "project"
    project.mkdir()
    make_final_ready_fixture(project, freeze_artifacts=False)
    other = project / "03_结果表格/other.csv"
    other.write_text("metric,value\nother,2\n", encoding="utf-8")
    qc = project / QC_REL
    runs = read_rows(qc / "run_record.csv")
    runs[0]["output_tables"] = "03_结果表格/other.csv"
    write_rows(qc / "run_record.csv", runs)
    freeze_run_artifacts(project, "R1")

    summary = evaluate(project, "final")

    assert summary["readiness"] == "blocked"
    integrity = next(check for check in summary["checks"] if check["id"] == "artifact_integrity")
    assert integrity["status"] == "fail"
    assert "03_结果表格/result.csv" in integrity["evidence"]


def test_unfrozen_candidate_rows_do_not_invalidate_frozen_paper_evidence(tmp_path: Path) -> None:
    project = tmp_path / "project"
    project.mkdir()
    make_final_ready_fixture(project)
    qc = project / QC_REL
    candidate = project / "03_结果表格/candidate.csv"
    candidate.write_text("metric,value\ncandidate,2\n", encoding="utf-8")
    rows = read_rows(qc / "result_registry.csv")
    rows.append({
        "result_id": "RSLT-CANDIDATE", "deliverable_id": "", "problem_id": "fixture",
        "scenario_id": "candidate", "metric": "candidate", "value": "2", "unit": "万元",
        "comparison_or_baseline": "", "source_table": "03_结果表格/candidate.csv",
        "source_figure": "", "source_script": "", "run_id": "",
        "validation_status": "candidate", "frozen_at": "", "superseded_by": "", "notes": "",
    })
    write_rows(qc / "result_registry.csv", rows)

    assert evaluate(project, "final")["readiness"] == "final_ready"


def test_cli_freezes_run_then_strictly_rejects_drift(tmp_path: Path) -> None:
    project = tmp_path / "project"
    project.mkdir()
    make_final_ready_fixture(project, freeze_artifacts=False)
    command = [
        sys.executable, str(SCRIPT_DIR / "contest_qc_gate.py"), str(project),
        "--freeze-run", "R1", "--phase", "final", "--strict",
    ]

    frozen = subprocess.run(command, text=True, capture_output=True, timeout=20)
    assert frozen.returncode == 0, frozen.stdout + frozen.stderr
    assert "Frozen run R1" in frozen.stdout

    (project / "03_结果表格/result.csv").write_text(
        "metric,value\nobjective,999\n", encoding="utf-8",
    )
    checked = subprocess.run(
        [item for item in command if item not in {"--freeze-run", "R1"}],
        text=True,
        capture_output=True,
        timeout=20,
    )
    assert checked.returncode == 1
    assert "blocked" in checked.stdout
    report = (project / QC_REL / "contest_qc_gate.md").read_text(encoding="utf-8")
    assert "artifact_integrity" in report
    assert "03_结果表格/result.csv" in report
