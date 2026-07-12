from __future__ import annotations

import json
from collections import Counter
from pathlib import Path
from typing import Any

from . import HARNESS_VERSION
from .contracts import DIMENSIONS
from .grader import grade
from .paths import PathValidationError, validate_relative_path


def run_suite(fixtures_dir: Path) -> dict[str, Any]:
    fixtures_dir = fixtures_dir.resolve()
    expectations = json.loads((fixtures_dir / "expectations.json").read_text(encoding="utf-8"))
    if expectations.get("schema_version") != 1 or not isinstance(expectations.get("fixtures"), list):
        raise ValueError("fixture expectations schema is invalid")
    cases_dir = fixtures_dir.parent / "cases"
    rows: list[dict[str, Any]] = []
    failures: list[str] = []
    verdicts: Counter[str] = Counter()
    block_counts: Counter[str] = Counter()
    dimension_totals = {name: 0.0 for name in DIMENSIONS}
    dimension_counts = {name: 0 for name in DIMENSIONS}
    for expected in expectations["fixtures"]:
        case_id = expected["case_id"]
        fixture = expected["fixture"]
        try:
            if len(validate_relative_path(case_id).parts) != 1 or len(validate_relative_path(fixture).parts) != 1:
                raise PathValidationError("fixture identifiers must be single path segments")
        except (PathValidationError, TypeError) as exc:
            raise ValueError(f"unsafe fixture expectation: {case_id!r}/{fixture!r}") from exc
        result = grade(cases_dir / case_id, fixtures_dir / case_id / fixture)
        block_ids = sorted(item["id"] for item in result.hard_blocks)
        issues = []
        if result.verdict != expected["verdict"]:
            issues.append(f"verdict {result.verdict!r} != {expected['verdict']!r}")
        if block_ids != sorted(expected["hard_blocks"]):
            issues.append(f"hard blocks {block_ids!r} != {sorted(expected['hard_blocks'])!r}")
        if not float(expected["score_min"]) <= result.total_score <= float(expected["score_max"]):
            issues.append(f"score {result.total_score} outside expected range")
        fixture_id = f"{case_id}/{fixture}"
        failures.extend(f"{fixture_id}: {issue}" for issue in issues)
        rows.append({"fixture_id": fixture_id, "verdict": result.verdict, "score": result.total_score, "hard_blocks": block_ids, "expectation_passed": not issues})
        verdicts[result.verdict] += 1
        block_counts.update(block_ids)
        for name, score in result.dimension_scores.items():
            dimension_totals[name] += score
            dimension_counts[name] += 1
    means = {name: round(dimension_totals[name] / dimension_counts[name], 6) if dimension_counts[name] else 0.0 for name in DIMENSIONS}
    return {
        "harness_version": HARNESS_VERSION,
        "fixture_count": len(rows),
        "passed_expectations": len(rows) - len({item.split(":", 1)[0] for item in failures}),
        "failed_expectations": failures,
        "verdict_counts": dict(sorted(verdicts.items())),
        "hard_block_counts": dict(sorted(block_counts.items())),
        "dimension_means": means,
        "fixtures": rows,
    }


def suite_json(result: dict[str, Any]) -> str:
    return json.dumps(result, ensure_ascii=False, indent=2, sort_keys=True, allow_nan=False) + "\n"


def suite_markdown(result: dict[str, Any]) -> str:
    lines = [
        "# Benchmark Suite",
        "",
        f"- Expectations: `{result['passed_expectations']}/{result['fixture_count']}` passed",
        f"- Harness: `{result['harness_version']}`",
        "",
        "| Fixture | Verdict | Score | Expected |",
        "|---|---|---:|---|",
    ]
    lines.extend(f"| {row['fixture_id']} | {row['verdict']} | {row['score']:.2f} | {'pass' if row['expectation_passed'] else 'fail'} |" for row in result["fixtures"])
    if result["failed_expectations"]:
        lines.extend(["", "## Failed Expectations", ""])
        lines.extend(f"- {item}" for item in result["failed_expectations"])
    lines.extend(["", "> This synthetic benchmark is a regression signal, not a prediction of competition awards.", ""])
    return "\n".join(lines)


def write_suite(result: dict[str, Any], output_dir: Path) -> tuple[Path, Path]:
    output_dir.mkdir(parents=True, exist_ok=True)
    json_path = output_dir / "benchmark_suite.json"
    markdown_path = output_dir / "benchmark_suite.md"
    json_path.write_text(suite_json(result), encoding="utf-8")
    markdown_path.write_text(suite_markdown(result), encoding="utf-8")
    return json_path, markdown_path
