from __future__ import annotations

import json
from pathlib import Path

import pytest

from scripts.benchmark.contracts import ContractError, load_case, load_submission
from scripts.benchmark.rules import evaluate_rule

from scripts.tests.test_modeling_benchmark_grader import build_pair


def test_numeric_rule_has_exact_partial_and_failure_boundaries(tmp_path: Path) -> None:
    case_dir, submission_dir = build_pair(tmp_path)
    case = load_case(case_dir)
    submission = load_submission(submission_dir, case)
    rule = {"id": "metric", "dimension": "correctness", "type": "numeric", "weight": 1, "source": "solution", "path": "metrics.value", "expected": 10, "tolerance": 1, "partial_tolerance": 2}
    for value, expected_score in ((11, 1.0), (12, 0.5), (12.01, 0.0)):
        solution = dict(submission.solution)
        solution["metrics"] = {"value": value}
        changed = type(submission)(submission.root, solution, submission.run_record, submission.report)
        assert evaluate_rule(rule, case, changed).score == expected_score


def test_case_rejects_negative_or_reversed_tolerances(tmp_path: Path) -> None:
    case_dir, _ = build_pair(tmp_path)
    raw = json.loads((case_dir / "case.json").read_text())
    raw["rules"][0] = {"id": "bad", "dimension": "correctness", "type": "numeric", "weight": 1, "source": "solution", "path": "metrics.value", "expected": 1, "tolerance": 2, "partial_tolerance": 1}
    (case_dir / "case.json").write_text(json.dumps(raw))
    with pytest.raises(ContractError, match="tolerance"):
        load_case(case_dir)


def test_submission_rejects_negative_runtime_and_unsafe_evidence(tmp_path: Path) -> None:
    case_dir, submission_dir = build_pair(tmp_path)
    solution_path = submission_dir / "solution.json"
    solution = json.loads(solution_path.read_text())
    solution.update({"model_name": "demo", "model_version": "1", "random_seed": 1, "metrics": {}, "evidence": {"result": "../outside"}})
    solution_path.write_text(json.dumps(solution))
    with pytest.raises(ContractError, match="unsafe relative path"):
        load_submission(submission_dir, load_case(case_dir))
    solution["evidence"] = {}
    solution_path.write_text(json.dumps(solution))
    run_path = submission_dir / "run_record.json"
    run = json.loads(run_path.read_text())
    run.update({"command": "python demo.py", "runtime_seconds": -1})
    run_path.write_text(json.dumps(run))
    with pytest.raises(ContractError, match="non-negative"):
        load_submission(submission_dir, load_case(case_dir))
