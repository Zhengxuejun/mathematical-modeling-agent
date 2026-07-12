from __future__ import annotations

from typing import Any


def render_tree(tree: dict[str, Any]) -> str:
    selected = tree.get("selected_candidate_id") or "none"
    lines = [
        "# Candidate Solution Tree",
        "",
        f"- Objective: `{tree['objective_metric']}` ({tree['direction']})",
        f"- Validation metric: `{tree['validation_metric']}`",
        f"- Candidates: `{len(tree['nodes'])}/{tree['max_candidates']}`",
        f"- Selected: `{selected}`",
        "",
        "| Candidate | Parent | Depth | Status | Label | Validation | Objective | Benchmark |",
        "|---|---|---:|---|---|---:|---:|---:|",
    ]
    for node in tree["nodes"]:
        evaluation = node.get("evaluation") or {}
        benchmark = evaluation.get("benchmark") or {}
        lines.append(
            "| {candidate_id} | {parent} | {depth} | {status} | {label} | {validation} | {objective} | {benchmark} |".format(
                candidate_id=node["candidate_id"],
                parent=node.get("parent_id") or "root",
                depth=node["depth"],
                status=node["status"],
                label=node["label"],
                validation=_format_number(evaluation.get("validation_score")),
                objective=_format_number(evaluation.get("objective")),
                benchmark=_format_number(benchmark.get("total_score")),
            )
        )
        if node.get("hypothesis"):
            lines.append(f"<!-- {node['candidate_id']} hypothesis: {node['hypothesis']} -->")
        reasons = evaluation.get("blocking_reasons") or []
        if reasons:
            lines.append(f"<!-- {node['candidate_id']} blocked: {'; '.join(reasons)} -->")
    if tree.get("selection_ranking"):
        lines.extend(["", "## Selection Ranking", ""])
        for index, item in enumerate(tree["selection_ranking"], 1):
            lines.append(f"{index}. `{item['candidate_id']}`: `{item['comparison']}`")
    lines.extend(
        [
            "",
            "> Selected means best eligible recorded candidate under this tree configuration. It does not imply paper_ready, final_ready, competition_ready, or an award prediction.",
            "",
        ]
    )
    return "\n".join(lines)


def _format_number(value: Any) -> str:
    return "-" if value is None else f"{float(value):.4f}"
