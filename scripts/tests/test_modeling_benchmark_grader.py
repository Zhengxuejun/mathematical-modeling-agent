from __future__ import annotations

import hashlib
import json
from pathlib import Path

from scripts.benchmark.grader import grade
from scripts.benchmark.reporting import result_json, result_markdown


DIMENSIONS = {"correctness": .3, "feasibility": .2, "statistical_validity": .15, "reproducibility": .15, "evidence_consistency": .1, "efficiency": .1}


def build_pair(tmp_path: Path, feasible: bool = True, exit_code: int = 0) -> tuple[Path, Path]:
    case = tmp_path / "demo"
    submission = tmp_path / "submission"
    (case / "input").mkdir(parents=True)
    submission.mkdir()
    data = b"value\n1\n"
    digest = hashlib.sha256(data).hexdigest()
    (case / "input/data.csv").write_bytes(data)
    rules = []
    for dimension in DIMENSIONS:
        rules.append({"id": dimension, "dimension": dimension, "type": "boolean", "weight": 1, "source": "solution", "path": f"checks.{dimension}", "expected": True, **({"hard_block": "mathematical"} if dimension == "feasibility" else {})})
    raw = {"schema_version": 1, "case_id": "demo", "category": "optimization", "difficulty": "micro", "dimensions": DIMENSIONS, "required_files": ["solution.json", "run_record.json", "report.md"], "input_files": [{"path": "input/data.csv", "sha256": digest}], "rules": rules}
    (case / "case.json").write_text(json.dumps(raw))
    (case / "expected.json").write_text("{}")
    checks = {key: True for key in DIMENSIONS}
    checks["feasibility"] = feasible
    (submission / "solution.json").write_text(json.dumps({"case_id": "demo", "model_name": "demo", "model_version": "1", "random_seed": 1, "metrics": {}, "checks": checks, "evidence": {}}))
    (submission / "run_record.json").write_text(json.dumps({"command": "python demo.py", "runtime_seconds": 0.01, "exit_code": exit_code, "input_hashes": {"input/data.csv": digest}, "artifacts": {}}))
    (submission / "report.md").write_text("report")
    return case, submission


def test_good_result_is_strong_and_reports_are_deterministic(tmp_path: Path) -> None:
    case, submission = build_pair(tmp_path)
    first = grade(case, submission)
    second = grade(case, submission)
    assert first.verdict == "strong"
    assert first.total_score == 100
    assert result_json(first) == result_json(second)
    assert result_markdown(first) == result_markdown(second)


def test_mathematical_failure_is_blocked_and_capped(tmp_path: Path) -> None:
    case, submission = build_pair(tmp_path, feasible=False)
    result = grade(case, submission)
    assert result.verdict == "blocked"
    assert result.total_score == 49.99
    assert result.hard_blocks == ({"id": "feasibility", "severity": "mathematical"},)


def test_bad_run_record_is_invalid(tmp_path: Path) -> None:
    case, submission = build_pair(tmp_path, exit_code=2)
    result = grade(case, submission)
    assert result.verdict == "invalid"
    assert result.total_score == 0
    assert result.hard_blocks[0]["id"] == "run_exit_code"
