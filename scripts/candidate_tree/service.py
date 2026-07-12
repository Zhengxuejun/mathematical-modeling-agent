from __future__ import annotations

import math
from pathlib import Path
from typing import Any

from scripts.benchmark.grader import grade

from .contracts import TreeError, load_json_object, new_tree
from .paths import project_relative, resolve_project_path, safe_relative_path, sha256_file
from .store import initialize, load_tree, mutate


def initialize_tree(
    project: Path,
    objective_metric: str,
    direction: str,
    validation_metric: str,
    max_candidates: int = 12,
    max_depth: int = 3,
) -> dict[str, Any]:
    tree = new_tree(objective_metric, direction, validation_metric, max_candidates, max_depth)
    initialize(project, tree)
    return tree


def add_candidate(
    project: Path,
    submission_path: str,
    label: str,
    hypothesis: str,
    parent_id: str | None = None,
) -> dict[str, Any]:
    submission = resolve_project_path(project, submission_path, directory=True)
    normalized = project_relative(project, submission)

    def add(tree: dict[str, Any]) -> dict[str, Any]:
        if len(tree["nodes"]) >= tree["max_candidates"]:
            raise TreeError("candidate limit reached")
        if any(node["submission_path"] == normalized for node in tree["nodes"]):
            raise TreeError(f"candidate submission is already registered: {normalized}")
        parent = _find_node(tree, parent_id) if parent_id else None
        depth = 0 if parent is None else parent["depth"] + 1
        if depth > tree["max_depth"]:
            raise TreeError("candidate depth limit reached")
        next_number = max((int(node["candidate_id"][1:]) for node in tree["nodes"]), default=0) + 1
        if next_number > 999:
            raise TreeError("candidate id space exhausted")
        node = {
            "candidate_id": f"C{next_number:03d}",
            "parent_id": parent_id,
            "depth": depth,
            "submission_path": normalized,
            "label": _required_text(label, "label"),
            "hypothesis": _required_text(hypothesis, "hypothesis"),
            "status": "registered",
            "evaluation": None,
        }
        tree["nodes"].append(node)
        tree["selection_ranking"] = []
        return node

    _, node = mutate(project, add)
    return node


def evaluate_candidate(project: Path, candidate_id: str, benchmark_case: Path | None = None) -> dict[str, Any]:
    benchmark_case = benchmark_case.resolve() if benchmark_case else None

    def evaluate(tree: dict[str, Any]) -> dict[str, Any]:
        node = _find_node(tree, candidate_id)
        submission = resolve_project_path(project, node["submission_path"], directory=True)
        evaluation = _evaluate_submission(tree, submission, benchmark_case)
        node["evaluation"] = evaluation
        node["status"] = "evaluated" if evaluation["eligible"] else "blocked"
        if tree.get("selected_candidate_id") == candidate_id and not evaluation["eligible"]:
            tree["selected_candidate_id"] = None
        elif tree.get("selected_candidate_id") == candidate_id:
            node["status"] = "selected"
        tree["selection_ranking"] = []
        return node

    _, node = mutate(project, evaluate)
    return node


def select_candidate(project: Path) -> dict[str, Any]:
    def select(tree: dict[str, Any]) -> dict[str, Any]:
        eligible = [node for node in tree["nodes"] if (node.get("evaluation") or {}).get("eligible") is True]
        if not eligible:
            raise TreeError("no eligible evaluated candidates")
        benchmark_values = [(node["evaluation"].get("benchmark") or {}).get("case_hash") for node in eligible]
        if any(benchmark_values):
            if not all(benchmark_values) or len(set(benchmark_values)) != 1:
                raise TreeError("eligible candidates have mixed or incomparable Benchmark coverage")
            use_benchmark = True
        else:
            use_benchmark = False
        ranked = sorted(eligible, key=lambda node: _selection_key(tree, node, use_benchmark))
        for node in tree["nodes"]:
            if node["status"] == "selected":
                node["status"] = "evaluated"
        winner = ranked[0]
        winner["status"] = "selected"
        tree["selected_candidate_id"] = winner["candidate_id"]
        tree["selection_ranking"] = [
            {
                "candidate_id": node["candidate_id"],
                "comparison": _comparison_text(tree, node, use_benchmark),
            }
            for node in ranked
        ]
        return winner

    _, winner = mutate(project, select)
    return winner


def get_tree(project: Path) -> dict[str, Any]:
    return load_tree(project)


def _evaluate_submission(tree: dict[str, Any], submission: Path, benchmark_case: Path | None) -> dict[str, Any]:
    gates = {
        "contract_valid": False,
        "run_succeeded": False,
        "feasible": False,
        "validation_passed": False,
        "evidence_verified": False,
    }
    reasons: list[str] = []
    objective: float | None = None
    validation_score: float | None = None
    runtime: float | None = None
    evidence_hashes: dict[str, str] = {}
    benchmark: dict[str, Any] | None = None
    try:
        solution = load_json_object(submission / "solution.json")
        run_record = load_json_object(submission / "run_record.json")
        try:
            (submission / "report.md").read_text(encoding="utf-8")
        except (OSError, UnicodeError) as exc:
            raise TreeError(f"cannot read report.md: {exc}") from exc
        _validate_identity(solution)
        objective = _finite_metric(solution, tree["objective_metric"])
        validation_score = _finite_metric(solution, tree["validation_metric"])
        if not 0 <= validation_score <= 1:
            raise TreeError("validation metric must be between 0 and 1")
        runtime = run_record.get("runtime_seconds")
        if not _finite_number(runtime) or runtime < 0:
            raise TreeError("runtime_seconds must be finite and non-negative")
        if not isinstance(run_record.get("command"), str) or not run_record["command"].strip():
            raise TreeError("run command must be a non-empty string")
        if not isinstance(run_record.get("exit_code"), int) or isinstance(run_record["exit_code"], bool):
            raise TreeError("exit_code must be an integer")
        gates["contract_valid"] = True
        gates["run_succeeded"] = run_record["exit_code"] == 0
        gates["feasible"] = solution["checks"].get("feasible") is True
        gates["validation_passed"] = solution["checks"].get("validation_passed") is True
        evidence_hashes = _verify_evidence(submission, solution, run_record)
        gates["evidence_verified"] = bool(evidence_hashes)
    except TreeError as exc:
        reasons.append(str(exc))
    for gate, passed in gates.items():
        if not passed and not reasons:
            reasons.append(gate.replace("_", " ") + " gate failed")
        elif not passed and gate != "contract_valid":
            reason = gate.replace("_", " ") + " gate failed"
            if reason not in reasons:
                reasons.append(reason)
    if benchmark_case is not None:
        result = grade(benchmark_case, submission)
        benchmark = {
            "case_id": result.case_id,
            "case_hash": result.case_hash,
            "verdict": result.verdict,
            "total_score": result.total_score,
            "hard_blocks": [item["id"] for item in result.hard_blocks],
        }
        gates["benchmark_eligible"] = result.verdict in {"pass", "strong"}
        if not gates["benchmark_eligible"]:
            reasons.append(f"Benchmark verdict is {result.verdict}")
    eligible = all(gates.values())
    return {
        "eligible": eligible,
        "gates": gates,
        "blocking_reasons": reasons,
        "objective": objective,
        "validation_score": validation_score,
        "runtime_seconds": runtime,
        "verified_evidence": evidence_hashes,
        "benchmark": benchmark,
    }


def _validate_identity(solution: dict[str, Any]) -> None:
    for field in ("model_name", "model_version"):
        if not isinstance(solution.get(field), str) or not solution[field].strip():
            raise TreeError(f"solution {field} must be a non-empty string")
    if not isinstance(solution.get("random_seed"), int) or isinstance(solution["random_seed"], bool):
        raise TreeError("solution random_seed must be an integer")
    for field in ("metrics", "checks", "evidence"):
        if not isinstance(solution.get(field), dict):
            raise TreeError(f"solution {field} must be an object")


def _finite_metric(solution: dict[str, Any], name: str) -> float:
    value = solution["metrics"].get(name)
    if not _finite_number(value):
        raise TreeError(f"metric {name!r} must be finite")
    return float(value)


def _finite_number(value: Any) -> bool:
    return isinstance(value, (int, float)) and not isinstance(value, bool) and math.isfinite(value)


def _verify_evidence(submission: Path, solution: dict[str, Any], run_record: dict[str, Any]) -> dict[str, str]:
    evidence = solution["evidence"]
    artifacts = run_record.get("artifacts")
    if not evidence:
        raise TreeError("candidate must declare at least one evidence file")
    if not isinstance(artifacts, dict):
        raise TreeError("run_record artifacts must be an object")
    verified: dict[str, str] = {}
    for claim, relative in sorted(evidence.items()):
        if not isinstance(claim, str) or not claim or not isinstance(relative, str):
            raise TreeError("evidence claims and paths must be non-empty strings")
        safe_relative_path(relative)
        path = _resolve_submission_file(submission, relative)
        actual_hash = sha256_file(path)
        if artifacts.get(relative) != actual_hash:
            raise TreeError(f"evidence hash mismatch: {relative}")
        verified[relative] = actual_hash
    return verified


def _resolve_submission_file(submission: Path, relative: str) -> Path:
    path = safe_relative_path(relative)
    root = submission.resolve(strict=True)
    try:
        resolved = root.joinpath(*path.parts).resolve(strict=True)
        resolved.relative_to(root)
    except (FileNotFoundError, ValueError) as exc:
        raise TreeError(f"evidence path is missing or escapes submission: {relative}") from exc
    if not resolved.is_file():
        raise TreeError(f"evidence path is not a file: {relative}")
    return resolved


def _selection_key(tree: dict[str, Any], node: dict[str, Any], use_benchmark: bool) -> tuple[Any, ...]:
    evaluation = node["evaluation"]
    benchmark_score = float(evaluation["benchmark"]["total_score"]) if use_benchmark else 0.0
    objective = float(evaluation["objective"])
    objective_key = -objective if tree["direction"] == "maximize" else objective
    return (
        -benchmark_score,
        -float(evaluation["validation_score"]),
        objective_key,
        -len(evaluation["verified_evidence"]),
        float(evaluation["runtime_seconds"]),
        node["candidate_id"],
    )


def _comparison_text(tree: dict[str, Any], node: dict[str, Any], use_benchmark: bool) -> str:
    evaluation = node["evaluation"]
    parts = []
    if use_benchmark:
        parts.append(f"benchmark={evaluation['benchmark']['total_score']:.2f}")
    parts.extend(
        [
            f"validation={evaluation['validation_score']:.4f}",
            f"{tree['objective_metric']}={evaluation['objective']:.6g}",
            f"evidence={len(evaluation['verified_evidence'])}",
            f"runtime={evaluation['runtime_seconds']:.4f}s",
        ]
    )
    return ", ".join(parts)


def _find_node(tree: dict[str, Any], candidate_id: str | None) -> dict[str, Any]:
    for node in tree["nodes"]:
        if node["candidate_id"] == candidate_id:
            return node
    raise TreeError(f"unknown candidate id: {candidate_id}")


def _required_text(value: str, field: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise TreeError(f"{field} must be a non-empty string")
    return value.strip()
