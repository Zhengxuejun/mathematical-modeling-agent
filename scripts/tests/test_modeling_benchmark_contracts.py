from __future__ import annotations

import hashlib
import json
from pathlib import Path

import pytest

from scripts.benchmark.contracts import ContractError, load_case
from scripts.benchmark.paths import PathValidationError, resolve_local_file


def write_case(root: Path) -> None:
    root.mkdir()
    (root / "input").mkdir()
    data = b"x,y\n1,2\n"
    (root / "input/data.csv").write_bytes(data)
    case = {
        "schema_version": 1,
        "case_id": root.name,
        "category": "optimization",
        "difficulty": "micro",
        "dimensions": {"correctness": .3, "feasibility": .2, "statistical_validity": .15, "reproducibility": .15, "evidence_consistency": .1, "efficiency": .1},
        "required_files": ["solution.json", "run_record.json", "report.md"],
        "input_files": [{"path": "input/data.csv", "sha256": hashlib.sha256(data).hexdigest()}],
        "rules": [{"id": "objective", "dimension": "correctness", "type": "numeric", "weight": 1, "source": "solution", "path": "outputs.objective", "expected_path": "objective"}],
    }
    (root / "case.json").write_text(json.dumps(case), encoding="utf-8")
    (root / "expected.json").write_text('{"objective": 2}', encoding="utf-8")


def test_load_valid_case_and_reject_bad_weights_and_duplicate_rules(tmp_path: Path) -> None:
    root = tmp_path / "demo"
    write_case(root)
    assert load_case(root).case_id == "demo"
    raw = json.loads((root / "case.json").read_text())
    raw["dimensions"]["correctness"] = .4
    (root / "case.json").write_text(json.dumps(raw))
    with pytest.raises(ContractError, match="sum to 1"):
        load_case(root)
    raw["dimensions"]["correctness"] = .3
    raw["rules"].append(dict(raw["rules"][0]))
    (root / "case.json").write_text(json.dumps(raw))
    with pytest.raises(ContractError, match="duplicate"):
        load_case(root)


def test_case_rejects_input_hash_mismatch(tmp_path: Path) -> None:
    root = tmp_path / "demo"
    write_case(root)
    (root / "input/data.csv").write_text("changed")
    with pytest.raises(ContractError, match="hash mismatch"):
        load_case(root)


def test_case_rejects_missing_expected_value(tmp_path: Path) -> None:
    root = tmp_path / "demo"
    write_case(root)
    (root / "expected.json").write_text("{}")
    with pytest.raises(ContractError, match="missing expected value"):
        load_case(root)


def test_case_rejects_non_finite_json_number(tmp_path: Path) -> None:
    root = tmp_path / "demo"
    write_case(root)
    (root / "expected.json").write_text('{"objective": NaN}')
    with pytest.raises(ContractError, match="valid JSON"):
        load_case(root)


def test_path_helper_rejects_traversal_absolute_and_escaping_symlink(tmp_path: Path) -> None:
    root = tmp_path / "root"
    root.mkdir()
    outside = tmp_path / "outside.txt"
    outside.write_text("secret")
    (root / "link").symlink_to(outside)
    for value in ("../outside.txt", str(outside), "link"):
        with pytest.raises(PathValidationError):
            resolve_local_file(root, value)
