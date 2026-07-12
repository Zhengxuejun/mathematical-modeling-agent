from __future__ import annotations

import json
from pathlib import Path

from .grader import BenchmarkResult


def result_json(result: BenchmarkResult) -> str:
    return json.dumps(result.to_dict(), ensure_ascii=False, indent=2, sort_keys=True, allow_nan=False) + "\n"


def result_markdown(result: BenchmarkResult) -> str:
    lines = [
        f"# Benchmark Result: {result.case_id}",
        "",
        f"- Verdict: `{result.verdict}`",
        f"- Score: `{result.total_score:.2f}` (raw `{result.raw_score:.2f}`)",
        f"- Harness: `{result.harness_version}`",
        "",
        "## Dimensions",
        "",
        "| Dimension | Score |",
        "|---|---:|",
    ]
    lines.extend(f"| {name} | {score:.3f} |" for name, score in sorted(result.dimension_scores.items()))
    lines.extend(["", "## Rule Results", "", "| Rule | Status | Score |", "|---|---|---:|"])
    lines.extend(f"| {item.rule_id} | {item.status} | {item.score:.2f} |" for item in result.rule_results)
    if result.hard_blocks:
        lines.extend(["", "## Hard Blocks", ""])
        lines.extend(f"- `{item['id']}` ({item['severity']})" for item in result.hard_blocks)
    if result.errors:
        lines.extend(["", "## Errors", ""])
        lines.extend(f"- {item}" for item in result.errors)
    lines.extend(["", "> This synthetic benchmark is a regression signal, not a prediction of competition awards.", ""])
    return "\n".join(lines)


def write_result(result: BenchmarkResult, output_dir: Path) -> tuple[Path, Path]:
    output_dir.mkdir(parents=True, exist_ok=True)
    json_path = output_dir / "benchmark_result.json"
    markdown_path = output_dir / "benchmark_result.md"
    json_path.write_text(result_json(result), encoding="utf-8")
    markdown_path.write_text(result_markdown(result), encoding="utf-8")
    return json_path, markdown_path
