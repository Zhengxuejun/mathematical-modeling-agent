from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Any

from .contracts import CaseContract, SubmissionContract, lookup
from .paths import PathValidationError, resolve_local_file, sha256_file


@dataclass(frozen=True)
class RuleResult:
    rule_id: str
    dimension: str
    status: str
    score: float
    weight: float
    message: str
    hard_block: str | None = None


def _actual(rule: dict[str, Any], case: CaseContract, submission: SubmissionContract) -> Any:
    source = rule.get("source", "solution")
    roots = {"solution": submission.solution, "run_record": submission.run_record, "expected": case.expected}
    if source == "report":
        return submission.report
    return lookup(roots[source], rule["path"])


def evaluate_rule(rule: dict[str, Any], case: CaseContract, submission: SubmissionContract) -> RuleResult:
    score = 0.0
    message = "rule failed"
    try:
        actual = _actual(rule, case, submission)
        expected = rule.get("expected")
        if "expected_path" in rule:
            expected = lookup(case.expected, rule["expected_path"])
        kind = rule["type"]
        if kind in {"boolean", "exact"}:
            score = 1.0 if actual == expected else 0.0
        elif kind == "numeric":
            if isinstance(actual, bool) or not isinstance(actual, (int, float)) or not math.isfinite(actual):
                score = 0.0
            else:
                distance = abs(float(actual) - float(expected))
                tolerance = float(rule.get("tolerance", 0.0))
                partial = float(rule.get("partial_tolerance", tolerance))
                score = 1.0 if distance <= tolerance else (0.5 if distance <= partial else 0.0)
        elif kind == "range":
            score = 1.0 if float(rule["minimum"]) <= float(actual) <= float(rule["maximum"]) else 0.0
        elif kind == "ranking":
            actual_list = list(actual)
            expected_list = list(expected)
            score = 1.0 if actual_list == expected_list else (0.5 if actual_list[:1] == expected_list[:1] else 0.0)
        elif kind == "evidence":
            relative = str(actual)
            artifact = resolve_local_file(submission.root, relative)
            declared = submission.run_record.get("artifacts", {}).get(relative)
            score = 1.0 if declared == sha256_file(artifact) else 0.0
        elif kind == "report_contains":
            score = 1.0 if str(expected) in str(actual) else 0.0
        elif kind == "runtime":
            seconds = float(actual)
            budget = float(rule["maximum"])
            score = 1.0 if seconds <= budget else (0.5 if seconds <= budget * 2 else 0.0)
        message = "rule passed" if score == 1.0 else ("partial credit" if score > 0 else "rule failed")
    except (KeyError, TypeError, ValueError, PathValidationError):
        score = 0.0
        message = "required value or evidence is missing or invalid"
    hard_block = rule.get("hard_block") if score == 0 else None
    return RuleResult(rule["id"], rule["dimension"], "pass" if score == 1 else ("partial" if score > 0 else "fail"), score, float(rule["weight"]), message, hard_block)

