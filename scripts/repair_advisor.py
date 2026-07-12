#!/usr/bin/env python3
"""Generate prioritized repair advice and delivery readiness summary.

Reads existing audit outputs:
  - 06_过程记录/pipeline/pipeline_run_summary.json
  - 06_过程记录/质量门禁/quality_gate_plus.json
  - 06_过程记录/问题覆盖/problem_coverage.json
  - 06_过程记录/结果解释/result_interpretation_draft.json
  - 06_过程记录/报告拼装/report_section_assembly.json
  - 06_过程记录/一致性检查/auto_report_audit.json
  - 07_提交包/submission_manifest.json

Writes:
  - 06_过程记录/修复建议/repair_advice.json
  - 06_过程记录/修复建议/repair_advice.md

The goal is not to add another gate; it translates scattered failures/warnings
into an actionable "can submit / what to fix first" checklist.
"""
from __future__ import annotations

import argparse
import json
import sys
from dataclasses import asdict, dataclass
from datetime import datetime
from pathlib import Path
from typing import Any


@dataclass
class Advice:
    priority: int
    severity: str  # fail/warn/info
    source: str
    item: str
    problem: str
    action: str
    evidence: str = ""


def load_json(path: Path) -> dict[str, Any]:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return {}


def add(advice: list[Advice], priority: int, severity: str, source: str, item: str, problem: str, action: str, evidence: str = "") -> None:
    advice.append(Advice(priority, severity, source, item, problem, action, evidence))


def ingest_findings(advice: list[Advice], source: str, findings: list[dict[str, Any]], fail_base: int, warn_base: int) -> None:
    for f in findings or []:
        status = str(f.get("status", ""))
        if status not in {"fail", "warn"}:
            continue
        item = str(f.get("item") or f.get("name") or "unknown")
        detail = str(f.get("detail") or "")
        evidence = str(f.get("evidence") or "")
        if status == "fail":
            action = action_for_item(item, detail, severe=True)
            add(advice, fail_base, "fail", source, item, detail or f"{item} failed", action, evidence)
        else:
            action = action_for_item(item, detail, severe=False)
            add(advice, warn_base, "warn", source, item, detail or f"{item} warning", action, evidence)


def action_for_item(item: str, detail: str, severe: bool) -> str:
    name = item.lower()
    if "referenced_tables" in name or "table_file_refs" in name:
        return "检查报告中显式引用的结果表文件名；若文件真实存在，改成准确文件名；若不存在，补表或删除引用。"
    if "referenced_figures" in name or "figure_file_refs" in name:
        return "检查报告中显式引用的图表文件名；补齐 `04_图表/` 中缺失图，或修正报告引用。"
    if "report" in name and ("exist" in name or "报告" in detail):
        return "补充或指定正式报告文件，优先放入 `05_报告定稿/`，再重新运行报告审计与 pipeline。"
    if "unreferenced_result" in name:
        return "把交付目录中的结果表在报告/附录中显式解释；若只是中间产物，移出最终结果目录。"
    if "unreferenced_figure" in name:
        return "在报告正文或附录中引用并解释未引用图表；若只是调试图，移出最终图表目录。"
    if "numbers" in name or "numeric" in name:
        return "核对报告中的关键数字是否来自结果表；同步更新报告数值或重新导出结果表。"
    if "baseline" in name:
        return "补充可运行 baseline/sanity check，并输出 `03_结果表格/baseline_results.*`。"
    if "sensitivity" in name or "robust" in name:
        return "补充敏感性/鲁棒性分析，输出 `03_结果表格/sensitivity_results.*` 并在报告中解释。"
    if "core" in name or "model_result" in name:
        return "补充主模型结果表，建议命名为 `model_results.csv` 或 `q*_model_results.csv`。"
    if "problem_analysis" in name:
        return "完善 `06_过程记录/problem_analysis.md`：逐问目标、数据清单、输出要求和题型路由必须具体。"
    if "coverage" in name or "missing" in detail or "漏答" in detail:
        return "回到 `problem_analysis.md` 和报告正文，确保每个小问都有直接回答、结果表和必要图表证据。"
    if "interpretation" in name or "without_tables" in detail:
        return "先补该小问结果表，再重新运行 `10_result_interpretation.py`；不要只补文字解释。"
    if "assembly" in name or "weak" in detail or "partial" in detail:
        return "查看 `06_过程记录/报告拼装/report_section_assembly.md`，补齐非 ready 小问的表格/图表证据。"
    if "final" in name or "package" in name or "submission" in name:
        return "重新运行 `finalize_modeling_project.py` 或 `02_代码/08_pipeline.py --zip`，确保提交包三件套完整。"
    if "state" in name:
        return "运行 `02_代码/07_update_state.py`，并检查状态机证据文件是否齐全。"
    if "tiny" in name or "figures_not_tiny" in name:
        return "重新生成真实图表文件，避免空白/占位/过小图片混入交付。"
    return "按该检查项说明补齐证据后，重新运行总控 pipeline 验证。"


def derive_from_counts(advice: list[Advice], source: str, counts: dict[str, Any]) -> None:
    if not counts:
        return
    if counts.get("missing_questions"):
        add(advice, 10, "fail", source, "missing_questions", f"存在 {counts.get('missing_questions')} 个漏答小问", "逐问补充报告回答；每问至少包含直接结论和对应证据。")
    if counts.get("weak_asset_questions"):
        add(advice, 20, "warn", source, "weak_asset_questions", f"存在 {counts.get('weak_asset_questions')} 个小问证据不足", "为弱证据小问补充结果表或图表，或在报告中解释无需该类证据。")
    if counts.get("drafts_without_tables"):
        add(advice, 15, "warn", source, "drafts_without_tables", f"存在 {counts.get('drafts_without_tables')} 个解释草稿缺表格", "先补结果表，再生成解释草稿，避免无证据解释。")
    if counts.get("weak_sections"):
        add(advice, 18, "warn", source, "weak_sections", f"存在 {counts.get('weak_sections')} 个报告骨架 weak 章节", "补齐该小问表格和图表证据，重新运行报告拼装器。")
    if counts.get("partial_sections"):
        add(advice, 24, "warn", source, "partial_sections", f"存在 {counts.get('partial_sections')} 个报告骨架 partial 章节", "补齐缺失的表格或图表证据，或明确说明无需该证据。")


def build(project: Path) -> dict[str, Any]:
    pipeline = load_json(project / "06_过程记录" / "pipeline" / "pipeline_run_summary.json")
    quality = load_json(project / "06_过程记录" / "质量门禁" / "quality_gate_plus.json")
    coverage = load_json(project / "06_过程记录" / "问题覆盖" / "problem_coverage.json")
    interpretation = load_json(project / "06_过程记录" / "结果解释" / "result_interpretation_draft.json")
    assembly = load_json(project / "06_过程记录" / "报告拼装" / "report_section_assembly.json")
    audit = load_json(project / "06_过程记录" / "一致性检查" / "auto_report_audit.json")
    manifest = load_json(project / "07_提交包" / "submission_manifest.json")

    advice: list[Advice] = []

    # Pipeline failed steps are top priority because they already reflect command-level breakage.
    for step in pipeline.get("steps", []) if isinstance(pipeline, dict) else []:
        if step.get("skipped"):
            continue
        if int(step.get("exit_code", 0) or 0) != 0:
            add(
                advice, 1, "fail", "pipeline", str(step.get("name") or "step"),
                f"步骤退出码={step.get('exit_code')}",
                "先查看 `06_过程记录/pipeline/pipeline_run_summary.md` 中该步骤 stdout/stderr，再修复对应脚本输出目录。",
                " ".join(step.get("command") or []),
            )

    # Structured findings.
    ingest_findings(advice, "quality_gate_plus", quality.get("findings", []), 8, 40)
    ingest_findings(advice, "auto_report_audit", audit.get("findings", []), 6, 35)
    if pipeline.get("phase") != "pre_finalize":
        ingest_findings(advice, "submission_manifest", manifest.get("checks", []), 7, 45)

    derive_from_counts(advice, "problem_coverage", coverage.get("counts", {}))
    derive_from_counts(advice, "result_interpretation", interpretation.get("counts", {}))
    derive_from_counts(advice, "report_section_assembly", assembly.get("counts", {}))

    # Global warnings from higher-level helpers.
    for src, obj in [("result_interpretation", interpretation), ("report_section_assembly", assembly)]:
        for i, w in enumerate(obj.get("global_warnings", []) if isinstance(obj, dict) else []):
            add(advice, 30, "warn", src, f"global_warning_{i+1}", str(w), "先处理该全局风险，再把生成草稿作为终稿依据。")

    # De-duplicate while keeping highest priority.
    dedup: dict[tuple[str, str, str], Advice] = {}
    for a in advice:
        key = (a.source, a.item, a.problem)
        if key not in dedup or a.priority < dedup[key].priority:
            dedup[key] = a
    advice = sorted(dedup.values(), key=lambda a: (a.priority, 0 if a.severity == "fail" else 1, a.source, a.item))

    fail_count = sum(1 for a in advice if a.severity == "fail")
    warn_count = sum(1 for a in advice if a.severity == "warn")
    pipeline_status = pipeline.get("recommended_status") if isinstance(pipeline, dict) else "unknown"
    highest_state = pipeline.get("highest_contiguous_state") if isinstance(pipeline, dict) else None
    if not pipeline_status:
        pipeline_status = "unknown"
    if fail_count:
        delivery_readiness = "blocked"
    elif warn_count:
        delivery_readiness = "needs_review"
    elif pipeline_status == "completed" and highest_state == "S8":
        delivery_readiness = "ready"
    else:
        delivery_readiness = "unknown"
        if not advice:
            add(advice, 60, "info", "repair_advisor", "insufficient_evidence", "未发现显式失败，但缺少 completed/S8 的完整 pipeline 证据。", "运行 `02_代码/08_pipeline.py --zip` 生成完整交付证据。")

    counts = {
        "advice_items": len(advice),
        "fail": fail_count,
        "warn": warn_count,
        "info": sum(1 for a in advice if a.severity == "info"),
    }
    return {
        "generated_at": datetime.now().isoformat(timespec="seconds"),
        "project": str(project),
        "delivery_readiness": delivery_readiness,
        "pipeline_status": pipeline_status,
        "highest_contiguous_state": highest_state,
        "counts": counts,
        "advice": [asdict(a) for a in advice],
    }


def write_outputs(project: Path, summary: dict[str, Any]) -> tuple[Path, Path]:
    out_dir = project / "06_过程记录" / "修复建议"
    out_dir.mkdir(parents=True, exist_ok=True)
    json_path = out_dir / "repair_advice.json"
    md_path = out_dir / "repair_advice.md"
    json_path.write_text(json.dumps(summary, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    c = summary["counts"]
    lines: list[str] = []
    lines.append("# 修复建议与交付摘要\n\n")
    lines.append(f"生成时间：{summary['generated_at']}\n\n")
    lines.append(f"项目：`{summary['project']}`\n\n")
    lines.append("## 交付判断\n\n")
    lines.append(f"- delivery_readiness：**{summary['delivery_readiness']}**\n")
    lines.append(f"- pipeline_status：`{summary.get('pipeline_status')}`\n")
    lines.append(f"- highest_contiguous_state：`{summary.get('highest_contiguous_state')}`\n")
    lines.append(f"- fail：{c['fail']}，warn：{c['warn']}，info：{c['info']}\n\n")

    if summary["delivery_readiness"] == "ready":
        lines.append("结论：当前自动证据显示可交付。仍需人工复核模型合理性、排版和题意吻合度。\n\n")
    elif summary["delivery_readiness"] == "blocked":
        lines.append("结论：当前不建议提交。先修复 fail 级问题，再重新运行 pipeline。\n\n")
    elif summary["delivery_readiness"] == "needs_review":
        lines.append("结论：无阻断性 fail，但存在 warning。正式提交前应逐项确认或消除。\n\n")
    else:
        lines.append("结论：证据不足，尚不能判断是否可交付。建议先运行完整 pipeline。\n\n")

    lines.append("## 优先修复清单\n\n")
    if not summary.get("advice"):
        lines.append("未发现自动修复建议。\n")
    else:
        lines.append("| 优先级 | 严重性 | 来源 | 项目 | 问题 | 建议动作 | 证据 |\n|---:|---|---|---|---|---|---|\n")
        for a in summary["advice"]:
            mark = {"fail": "❌ fail", "warn": "⚠️ warn", "info": "ℹ️ info"}.get(a["severity"], a["severity"])
            cells = [str(a["priority"]), mark, a["source"], a["item"], a["problem"], a["action"], a.get("evidence", "")]
            cells = [x.replace("|", "\\|").replace("\n", " ") for x in cells]
            lines.append("| " + " | ".join(cells) + " |\n")
    lines.append("\n## 推荐复验命令\n\n```bash\npython 02_代码/08_pipeline.py --zip --coverage-min-asset-hits 1\npython 02_代码/12_repair_advisor.py\n```\n")
    md_path.write_text("".join(lines), encoding="utf-8")
    return json_path, md_path


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("project")
    parser.add_argument("--strict", action="store_true", help="Return non-zero if delivery_readiness is not ready")
    args = parser.parse_args()
    project = Path(args.project).expanduser().resolve()
    if not project.exists():
        print(f"Project not found: {project}", file=sys.stderr)
        return 2
    summary = build(project)
    json_path, md_path = write_outputs(project, summary)
    c = summary["counts"]
    print(f"Repair advice: {md_path}")
    print(f"Repair advice json: {json_path}")
    print(f"Delivery readiness: {summary['delivery_readiness']}; fail={c['fail']}, warn={c['warn']}, info={c['info']}")
    if args.strict and summary["delivery_readiness"] != "ready":
        return 1
    if c["fail"]:
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
