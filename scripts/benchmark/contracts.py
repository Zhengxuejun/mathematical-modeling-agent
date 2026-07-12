from __future__ import annotations

import json
import math
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from .paths import PathValidationError, resolve_local_file, sha256_file, validate_relative_path

DIMENSIONS = (
    "correctness",
    "feasibility",
    "statistical_validity",
    "reproducibility",
    "evidence_consistency",
    "efficiency",
)
CORE_DIMENSIONS = DIMENSIONS[:4]
RULE_TYPES = {"boolean", "exact", "numeric", "range", "ranking", "evidence", "report_contains", "runtime"}
JSON_SOURCES = {"solution", "run_record", "expected"}
SHA256_RE = re.compile(r"[0-9a-f]{64}")


class ContractError(ValueError):
    pass


def _load_json(path: Path) -> dict[str, Any]:
    try:
        value = json.loads(path.read_text(encoding="utf-8"), parse_constant=lambda value: (_ for _ in ()).throw(ValueError(value)))
    except (OSError, UnicodeError, json.JSONDecodeError, ValueError) as exc:
        raise ContractError(f"cannot read valid JSON from {path}: {exc}") from exc
    if not isinstance(value, dict):
        raise ContractError(f"JSON root must be an object: {path}")
    _reject_non_finite(value)
    return value


def _reject_non_finite(value: Any, location: str = "root") -> None:
    if isinstance(value, float) and not math.isfinite(value):
        raise ContractError(f"non-finite number at {location}")
    if isinstance(value, dict):
        for key, item in value.items():
            _reject_non_finite(item, f"{location}.{key}")
    elif isinstance(value, list):
        for index, item in enumerate(value):
            _reject_non_finite(item, f"{location}[{index}]")


@dataclass(frozen=True)
class CaseContract:
    root: Path
    case_id: str
    category: str
    difficulty: str
    dimensions: dict[str, float]
    required_files: tuple[str, ...]
    input_files: tuple[dict[str, str], ...]
    rules: tuple[dict[str, Any], ...]
    expected: dict[str, Any]


@dataclass(frozen=True)
class SubmissionContract:
    root: Path
    solution: dict[str, Any]
    run_record: dict[str, Any]
    report: str


def load_case(root: Path) -> CaseContract:
    root = root.resolve()
    raw = _load_json(root / "case.json")
    expected = _load_json(root / "expected.json")
    if raw.get("schema_version") != 1:
        raise ContractError("case schema_version must be 1")
    case_id = raw.get("case_id")
    if not isinstance(case_id, str) or not case_id or root.name != case_id:
        raise ContractError("case_id must be non-empty and match the directory name")
    for field in ("category", "difficulty"):
        if not isinstance(raw.get(field), str) or not raw[field]:
            raise ContractError(f"case {field} must be a non-empty string")
    dimensions = raw.get("dimensions")
    if not isinstance(dimensions, dict) or set(dimensions) != set(DIMENSIONS):
        raise ContractError(f"dimensions must contain exactly: {', '.join(DIMENSIONS)}")
    if any(not isinstance(weight, (int, float)) or isinstance(weight, bool) or weight < 0 for weight in dimensions.values()):
        raise ContractError("dimension weights must be non-negative numbers")
    if not math.isclose(sum(dimensions.values()), 1.0, abs_tol=1e-9):
        raise ContractError("dimension weights must sum to 1")

    required_files = raw.get("required_files")
    if not isinstance(required_files, list) or not required_files:
        raise ContractError("required_files must be a non-empty list")
    if len(required_files) != len(set(required_files)) or not {"solution.json", "run_record.json", "report.md"}.issubset(required_files):
        raise ContractError("required_files must uniquely include solution.json, run_record.json, and report.md")
    for path in required_files:
        try:
            validate_relative_path(path)
        except PathValidationError as exc:
            raise ContractError(str(exc)) from exc

    input_files = raw.get("input_files")
    if not isinstance(input_files, list) or not input_files:
        raise ContractError("input_files must be a non-empty list")
    input_paths: set[str] = set()
    for item in input_files:
        if not isinstance(item, dict) or set(item) != {"path", "sha256"}:
            raise ContractError("each input file needs path and sha256")
        if item["path"] in input_paths:
            raise ContractError(f"duplicate input path: {item['path']}")
        input_paths.add(item["path"])
        if not isinstance(item.get("sha256"), str) or not SHA256_RE.fullmatch(item["sha256"]):
            raise ContractError("input sha256 must be 64 lowercase hexadecimal characters")
        try:
            path = resolve_local_file(root, item["path"])
        except (PathValidationError, TypeError) as exc:
            raise ContractError(str(exc)) from exc
        if sha256_file(path) != item["sha256"]:
            raise ContractError(f"input hash mismatch: {item['path']}")

    rules = raw.get("rules")
    if not isinstance(rules, list) or not rules:
        raise ContractError("rules must be a non-empty list")
    ids: set[str] = set()
    for rule in rules:
        if not isinstance(rule, dict) or not isinstance(rule.get("id"), str):
            raise ContractError("every rule needs a string id")
        if rule["id"] in ids:
            raise ContractError(f"duplicate rule id: {rule['id']}")
        ids.add(rule["id"])
        if rule.get("dimension") not in DIMENSIONS or rule.get("type") not in RULE_TYPES:
            raise ContractError(f"invalid rule: {rule['id']}")
        weight = rule.get("weight")
        if not isinstance(weight, (int, float)) or isinstance(weight, bool) or weight <= 0:
            raise ContractError(f"rule weight must be positive: {rule['id']}")
        if rule.get("hard_block") not in {None, "integrity", "mathematical", "statistical"}:
            raise ContractError(f"invalid hard block: {rule['id']}")
        source = rule.get("source", "solution")
        if source not in JSON_SOURCES | {"report"} or not isinstance(rule.get("path"), str):
            raise ContractError(f"invalid rule source or path: {rule['id']}")
        if rule["type"] == "numeric":
            tolerance = rule.get("tolerance", 0)
            partial = rule.get("partial_tolerance", tolerance)
            if any(not isinstance(value, (int, float)) or isinstance(value, bool) or value < 0 for value in (tolerance, partial)) or partial < tolerance:
                raise ContractError(f"invalid tolerance: {rule['id']}")
        if rule["type"] in {"range", "runtime"}:
            values = [rule.get("maximum")]
            if rule["type"] == "range":
                values.append(rule.get("minimum"))
            if any(not isinstance(value, (int, float)) or isinstance(value, bool) or not math.isfinite(value) for value in values):
                raise ContractError(f"invalid range: {rule['id']}")
            if rule["type"] == "range" and rule["minimum"] > rule["maximum"]:
                raise ContractError(f"invalid range: {rule['id']}")
            if rule["type"] == "runtime" and rule["maximum"] < 0:
                raise ContractError(f"invalid runtime budget: {rule['id']}")
        if "expected_path" in rule:
            if not isinstance(rule["expected_path"], str):
                raise ContractError(f"invalid expected path: {rule['id']}")
            try:
                lookup(expected, rule["expected_path"])
            except KeyError as exc:
                raise ContractError(f"missing expected value for rule: {rule['id']}") from exc
    return CaseContract(root, case_id, raw["category"], raw["difficulty"], dict(dimensions), tuple(required_files), tuple(input_files), tuple(rules), expected)


def load_submission(root: Path, case: CaseContract) -> SubmissionContract:
    root = root.resolve()
    for relative in case.required_files:
        try:
            resolve_local_file(root, relative)
        except PathValidationError as exc:
            raise ContractError(str(exc)) from exc
    solution = _load_json(root / "solution.json")
    run_record = _load_json(root / "run_record.json")
    if solution.get("case_id") != case.case_id:
        raise ContractError("submission case_id mismatch")
    for field in ("model_name", "model_version"):
        if not isinstance(solution.get(field), str) or not solution[field]:
            raise ContractError(f"solution {field} must be a non-empty string")
    if not isinstance(solution.get("random_seed"), int) or isinstance(solution["random_seed"], bool):
        raise ContractError("solution random_seed must be an integer")
    for field in ("metrics", "checks", "evidence"):
        if not isinstance(solution.get(field), dict):
            raise ContractError(f"solution {field} must be an object")
    for value in solution["evidence"].values():
        try:
            validate_relative_path(value)
        except (PathValidationError, TypeError) as exc:
            raise ContractError(str(exc)) from exc
    if not isinstance(run_record.get("command"), str) or not run_record["command"]:
        raise ContractError("run_record command must be a non-empty string")
    runtime = run_record.get("runtime_seconds")
    if not isinstance(runtime, (int, float)) or isinstance(runtime, bool) or not math.isfinite(runtime) or runtime < 0:
        raise ContractError("run_record runtime_seconds must be finite and non-negative")
    if not isinstance(run_record.get("exit_code"), int) or isinstance(run_record["exit_code"], bool):
        raise ContractError("run_record exit_code must be an integer")
    for field in ("input_hashes", "artifacts"):
        values = run_record.get(field)
        if not isinstance(values, dict):
            raise ContractError(f"run_record {field} must be an object")
        for relative, digest in values.items():
            try:
                validate_relative_path(relative)
            except (PathValidationError, TypeError) as exc:
                raise ContractError(str(exc)) from exc
            if not isinstance(digest, str) or not SHA256_RE.fullmatch(digest):
                raise ContractError(f"run_record {field} contains an invalid SHA-256")
    try:
        report = (root / "report.md").read_text(encoding="utf-8")
    except (OSError, UnicodeError) as exc:
        raise ContractError(f"cannot read report.md: {exc}") from exc
    return SubmissionContract(root, solution, run_record, report)


def lookup(value: Any, dotted_path: str) -> Any:
    current = value
    for part in dotted_path.split("."):
        if not isinstance(current, dict) or part not in current:
            raise KeyError(dotted_path)
        current = current[part]
    return current
