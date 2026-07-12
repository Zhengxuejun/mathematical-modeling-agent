from __future__ import annotations

from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

from . import HARNESS_VERSION
from .contracts import CORE_DIMENSIONS, ContractError, load_case, load_submission
from .paths import sha256_file
from .rules import RuleResult, evaluate_rule


@dataclass(frozen=True)
class BenchmarkResult:
    harness_version: str
    case_id: str
    case_hash: str
    submission_hashes: dict[str, str]
    rule_results: tuple[RuleResult, ...]
    dimension_scores: dict[str, float]
    raw_score: float
    total_score: float
    hard_blocks: tuple[dict[str, str], ...]
    verdict: str
    errors: tuple[str, ...] = ()

    def to_dict(self) -> dict[str, Any]:
        value = asdict(self)
        value["rule_results"] = [asdict(item) for item in self.rule_results]
        value["hard_blocks"] = list(self.hard_blocks)
        value["errors"] = list(self.errors)
        return value


def _invalid(case_dir: Path, message: str) -> BenchmarkResult:
    return BenchmarkResult(HARNESS_VERSION, case_dir.name, "", {}, (), {}, 0.0, 0.0, ({"id": "contract_integrity", "severity": "integrity"},), "invalid", (message,))


def grade(case_dir: Path, submission_dir: Path) -> BenchmarkResult:
    try:
        case = load_case(case_dir)
        submission = load_submission(submission_dir, case)
    except ContractError as exc:
        return _invalid(case_dir, str(exc))

    integrity_errors: list[tuple[str, str]] = []
    if submission.run_record.get("exit_code") != 0:
        integrity_errors.append(("run_exit_code", "claimed run did not exit successfully"))
    declared_hashes = submission.run_record.get("input_hashes")
    if not isinstance(declared_hashes, dict):
        integrity_errors.append(("input_hashes", "run record has no input hashes"))
    else:
        for item in case.input_files:
            if declared_hashes.get(item["path"]) != item["sha256"]:
                integrity_errors.append(("input_hash_mismatch", item["path"]))
    if integrity_errors:
        result = _invalid(case_dir, "; ".join(message for _, message in integrity_errors))
        return BenchmarkResult(result.harness_version, case.case_id, sha256_file(case.root / "case.json"), {}, (), {}, 0.0, 0.0, tuple({"id": key, "severity": "integrity"} for key, _ in integrity_errors), "invalid", result.errors)

    rule_results = tuple(evaluate_rule(rule, case, submission) for rule in case.rules)
    dimension_scores: dict[str, float] = {}
    for dimension in case.dimensions:
        selected = [item for item in rule_results if item.dimension == dimension]
        total_weight = sum(item.weight for item in selected)
        dimension_scores[dimension] = round(sum(item.score * item.weight for item in selected) / total_weight, 6) if total_weight else 0.0
    raw_score = round(sum(dimension_scores[key] * case.dimensions[key] for key in case.dimensions) * 100, 2)
    blocks = tuple({"id": item.rule_id, "severity": str(item.hard_block)} for item in rule_results if item.hard_block)
    integrity = any(item["severity"] == "integrity" for item in blocks)
    blocked = any(item["severity"] in {"mathematical", "statistical"} for item in blocks)
    total_score = 0.0 if integrity else (min(raw_score, 49.99) if blocked else raw_score)
    if integrity:
        verdict = "invalid"
    elif blocked:
        verdict = "blocked"
    elif total_score >= 85 and all(dimension_scores.get(key, 0) >= .75 for key in CORE_DIMENSIONS):
        verdict = "strong"
    elif total_score >= 70 and all(dimension_scores.get(key, 0) >= .5 for key in CORE_DIMENSIONS):
        verdict = "pass"
    else:
        verdict = "needs_work"
    hashes = {path: sha256_file(submission.root / path) for path in case.required_files}
    return BenchmarkResult(HARNESS_VERSION, case.case_id, sha256_file(case.root / "case.json"), hashes, rule_results, dimension_scores, raw_score, total_score, blocks, verdict)

