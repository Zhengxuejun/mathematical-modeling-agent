#!/usr/bin/env python3
"""Assess competition-readiness for mathematical modeling projects.

This gate is deliberately stricter than S0-S8 workflow closure. It does not try
pretend that a project can be proven award-winning automatically; instead it
separates three levels:

1) workflow_ready: reproducible project artifacts exist.
2) model_ready: problem-specific model evidence exists and placeholder outputs
   have been replaced.
3) competition_ready: model results are validated, compared, risk-tested, and
   supported by a persuasive report/submission package.

The script is generic and uses file/content signals plus optional project-provided
metadata. Projects can strengthen evidence by writing
`06_过程记录/competition_evidence.json` with keys such as:

{
  "domain_checker": {"path": "02_代码/check_plan.py", "issue_count": 0},
  "official_templates_filled": ["03_结果表格/result1.xlsx"],
  "optimization_solver": {"type": "MIP", "status": "optimal", "objective": 123},
  "simulation": {"scenarios": 1000, "metrics": ["mean", "cvar_5"]},
  "model_comparison": true,
  "sensitivity_analysis": true,
  "paper_assets": {"figures": 5, "tables": 4}
}
"""
from __future__ import annotations

import argparse
import csv
import json
import math
import re
import sys
from dataclasses import dataclass, asdict
from pathlib import Path
from typing import Any

PLACEHOLDER_PATTERNS = [
    r"placeholder",
    r"baseline-derived",
    r"lightweight baseline",
    r"TODO",
    r"待补充",
    r"待完成",
    r"示例",
    r"replace with problem-specific",
    r"仅用于链路测试",
]
MODEL_KEYWORDS = [
    "目标函数", "约束", "决策变量", "状态变量", "参数估计", "优化", "整数规划", "线性规划", "非线性规划",
    "MIP", "MILP", "LP", "NLP", "DP", "动态规划", "蒙特卡洛", "Monte Carlo", "仿真", "回归", "预测", "评价", "TOPSIS",
    "AHP", "熵权", "随机森林", "ARIMA", "排队论", "网络流", "VRP", "TSP", "鲁棒", "敏感性",
]
VALIDATION_KEYWORDS = ["敏感性", "鲁棒", "误差", "检验", "交叉验证", "baseline", "基线", "对比", "置信", "CVaR", "分位数", "残差"]
REPORT_EXTS = {".md", ".docx", ".pdf", ".tex"}
TABLE_EXTS = {".csv", ".xlsx", ".xls", ".json"}
FIG_EXTS = {".png", ".jpg", ".jpeg", ".svg", ".pdf"}


@dataclass
class Check:
    id: str
    level: str  # workflow/model/competition
    status: str  # pass/warn/fail
    message: str
    evidence: str = ""


def read_text(path: Path, limit_chars: int = 2_000_000) -> str:
    try:
        if path.suffix.lower() == ".docx":
            # Lightweight docx text extraction without external dependencies.
            import zipfile
            import xml.etree.ElementTree as ET
            with zipfile.ZipFile(path) as z:
                xml = z.read("word/document.xml")
            root = ET.fromstring(xml)
            texts = [node.text or "" for node in root.iter() if node.tag.endswith("}t")]
            return "\n".join(texts)[:limit_chars]
        if path.suffix.lower() in {".pdf", ".xlsx", ".xls"}:
            return ""
        return path.read_text(encoding="utf-8", errors="ignore")[:limit_chars]
    except Exception:
        return ""


def read_json(path: Path) -> dict[str, Any]:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return {}


def list_files(root: Path, exts: set[str] | None = None) -> list[Path]:
    if not root.exists():
        return []
    files = [p for p in root.rglob("*") if p.is_file() and not p.name.startswith("~$")]
    if exts:
        files = [p for p in files if p.suffix.lower() in exts]
    return sorted(files)


def csv_nonempty(path: Path) -> bool:
    try:
        with path.open("r", encoding="utf-8-sig", errors="ignore", newline="") as f:
            rows = list(csv.reader(f))
        return len(rows) > 1 and any(any(str(x).strip() for x in row) for row in rows[1:])
    except Exception:
        return False


def contains_any(text: str, patterns: list[str]) -> bool:
    return any(re.search(p, text, flags=re.IGNORECASE) for p in patterns)


def count_keyword_hits(text: str, keywords: list[str]) -> int:
    low = text.lower()
    return sum(1 for kw in keywords if kw.lower() in low)


def evidence_json(project: Path) -> dict[str, Any]:
    candidates = [
        project / "06_过程记录" / "competition_evidence.json",
        project / "06_过程记录" / "竞赛证据" / "competition_evidence.json",
        project / "competition_evidence.json",
    ]
    for p in candidates:
        obj = read_json(p)
        if obj:
            obj["_path"] = str(p.relative_to(project))
            return obj
    return {}


def as_bool(value: Any) -> bool:
    if isinstance(value, bool):
        return value
    if isinstance(value, dict):
        # An explicit status is authoritative. Metadata such as paths, counts or
        # detected=true must never upgrade an explicit false/template/warn status.
        if "status" in value or "result" in value:
            raw_status = value.get("status", value.get("result"))
            if isinstance(raw_status, bool):
                return raw_status
            status = str(raw_status).strip().lower()
            if status in {"pass", "passed", "ok", "true", "ready", "optimal", "feasible"}:
                return True
            if status in {
                "false", "fail", "failed", "warn", "warning", "blocked", "unknown", "not_detected",
                "template_checker_only", "checker_detected_no_machine_output", "implemented_checker_warn",
                "implemented_checker_fail", "not_ready", "diagnostic-only",
            }:
                return False
        if "issue_count" in value:
            try:
                return int(value.get("issue_count")) == 0
            except Exception:
                return False
        return any(as_bool(v) for v in value.values())
    if isinstance(value, list):
        return len(value) > 0
    if isinstance(value, (int, float)):
        return math.isfinite(value) and value > 0
    if isinstance(value, str):
        return value.strip().lower() in {"true", "yes", "pass", "passed", "ready", "optimal", "feasible"}
    return False


def assess(project: Path) -> dict[str, Any]:
    checks: list[Check] = []
    raw_files = list_files(project / "01_原始数据") + list_files(project / "00_题目与资料")
    code_files = list_files(project / "02_代码", {".py", ".ipynb", ".m", ".r"})
    formal_code_files = [
        path for path in code_files
        if not any(part in {"generated_checkers", "generated_skeleton"} for part in path.parts)
    ]
    result_tables = list_files(project / "03_结果表格", TABLE_EXTS)
    figures = list_files(project / "04_图表", FIG_EXTS)
    reports = list_files(project / "05_报告定稿", REPORT_EXTS)
    evidence = evidence_json(project)

    pipeline = read_json(project / "06_过程记录" / "pipeline" / "pipeline_run_summary.json")
    quality = read_json(project / "06_过程记录" / "质量门禁" / "quality_gate_plus.json")
    coverage = read_json(project / "06_过程记录" / "问题覆盖" / "problem_coverage.json")
    repair = read_json(project / "06_过程记录" / "修复建议" / "repair_advice.json")
    audit = read_json(project / "06_过程记录" / "一致性检查" / "auto_report_audit.json")
    contest_qc = read_json(project / "06_过程记录" / "竞赛质控" / "contest_qc_gate.json")

    all_text_parts: list[str] = []
    for p in formal_code_files + reports + [project / "06_过程记录" / "problem_analysis.md"]:
        if p.exists():
            all_text_parts.append(read_text(p, limit_chars=300_000))
    all_text = "\n".join(all_text_parts)

    # Workflow level.
    checks.append(Check(
        "materials_present", "workflow", "pass" if raw_files else "fail",
        "题面/附件/原始数据已落盘" if raw_files else "缺少题面、附件或原始数据",
        f"files={len(raw_files)}",
    ))
    checks.append(Check(
        "problem_analysis_present", "workflow", "pass" if (project / "06_过程记录" / "problem_analysis.md").exists() and len(read_text(project / "06_过程记录" / "problem_analysis.md")) > 120 else "fail",
        "题目解析存在且非空" if (project / "06_过程记录" / "problem_analysis.md").exists() else "缺少 problem_analysis.md",
        "06_过程记录/problem_analysis.md",
    ))
    checks.append(Check(
        "result_assets_present", "workflow", "pass" if result_tables else "fail",
        "存在结果表" if result_tables else "缺少结果表",
        f"tables={len(result_tables)}",
    ))
    checks.append(Check(
        "report_present", "workflow", "pass" if reports else "fail",
        "存在报告/报告草稿" if reports else "缺少报告文件",
        f"reports={len(reports)}",
    ))
    if pipeline:
        checks.append(Check(
            "pipeline_status", "workflow", "pass" if pipeline.get("recommended_status") == "completed" else "warn",
            f"pipeline recommended_status={pipeline.get('recommended_status')}",
            "06_过程记录/pipeline/pipeline_run_summary.json",
        ))

    # Model level.
    placeholder_hits = contains_any(all_text, PLACEHOLDER_PATTERNS)
    nonempty_model_tables = [p for p in result_tables if p.suffix.lower() != ".csv" or csv_nonempty(p)]
    model_keyword_hits = count_keyword_hits(all_text, MODEL_KEYWORDS)
    main_model_code = [p for p in formal_code_files if re.search(r"(model|solve|solver|optimi|main|核心|主模型)", p.name, re.I)]

    checks.append(Check(
        "placeholder_replaced", "model", "fail" if placeholder_hits else "pass",
        "检测到 placeholder/TODO/链路测试表述，不能视为正式模型" if placeholder_hits else "未检测到明显 placeholder 表述",
    ))
    checks.append(Check(
        "problem_specific_model_evidence", "model", "pass" if (model_keyword_hits >= 4 and main_model_code) or as_bool(evidence.get("problem_specific_model")) else "warn",
        "存在题目特定模型/求解证据" if (model_keyword_hits >= 4 and main_model_code) else "缺少足够的题目特定模型证据：需要变量、目标函数、约束/算法与求解脚本",
        f"model_keyword_hits={model_keyword_hits}, model_code_files={len(main_model_code)}",
    ))
    checks.append(Check(
        "nonempty_model_results", "model", "pass" if nonempty_model_tables else "fail",
        "结果表非空" if nonempty_model_tables else "结果表为空或不可读",
        f"nonempty_tables={len(nonempty_model_tables)}",
    ))

    domain_checker = evidence.get("domain_checker") or evidence.get("constraint_checker")
    if domain_checker:
        checks.append(Check(
            "domain_checker", "model", "pass" if as_bool(domain_checker) else "fail",
            "领域约束/可行性 checker 通过" if as_bool(domain_checker) else "领域约束/可行性 checker 未通过",
            json.dumps(domain_checker, ensure_ascii=False)[:500],
        ))
    else:
        # Generic fallback: look for checker code/logs.
        checker_files = [p for p in code_files if re.search(r"(check|gate|verify|validate|audit|constraint|可行|约束)", p.name, re.I)]
        checks.append(Check(
            "domain_checker", "model", "warn" if checker_files else "fail",
            "发现检查脚本，但建议写入 competition_evidence.json 记录 issue_count" if checker_files else "缺少领域约束/可行性 checker 证据",
            f"checker_files={len(checker_files)}",
        ))

    official_templates = evidence.get("official_templates_filled") or evidence.get("required_outputs_filled")
    if official_templates is not None:
        ok = as_bool(official_templates)
        checks.append(Check(
            "required_outputs_filled", "model", "pass" if ok else "fail",
            "官方模板/题目要求输出已填写" if ok else "题目要求的官方模板/输出未填写",
            json.dumps(official_templates, ensure_ascii=False)[:500],
        ))

    # Competition level.
    qc_readiness = contest_qc.get("readiness") if isinstance(contest_qc, dict) else None
    qc_phase = contest_qc.get("phase") if isinstance(contest_qc, dict) else None
    if qc_readiness == "final_ready":
        checks.append(Check("contest_qc", "competition", "pass", "竞赛质控的最终证据/合规门禁通过", "06_过程记录/竞赛质控/contest_qc_gate.json"))
    elif qc_readiness == "blocked":
        checks.append(Check("contest_qc", "competition", "fail", "竞赛质控存在硬阻塞", "06_过程记录/竞赛质控/contest_qc_gate.md"))
    elif qc_readiness:
        checks.append(Check("contest_qc", "competition", "warn", f"竞赛质控 phase={qc_phase}, readiness={qc_readiness}", "06_过程记录/竞赛质控/contest_qc_gate.md"))
    else:
        checks.append(Check("contest_qc", "competition", "warn", "缺少 contest_qc_gate 证据；终稿前必须运行最终质控", "06_过程记录/竞赛质控/contest_qc_gate.py"))

    coverage_counts = coverage.get("counts", {}) if isinstance(coverage, dict) else {}
    if coverage_counts:
        missing = int(coverage_counts.get("missing_questions", 0) or 0)
        weak = int(coverage_counts.get("weak_asset_questions", 0) or 0)
        checks.append(Check(
            "per_question_coverage", "competition", "pass" if missing == 0 and weak == 0 else "warn",
            f"逐问覆盖 missing={missing}, weak_assets={weak}",
            "06_过程记录/问题覆盖/problem_coverage.json",
        ))
    else:
        checks.append(Check("per_question_coverage", "competition", "warn", "缺少逐问覆盖追踪结果"))

    validation_hits = count_keyword_hits(all_text, VALIDATION_KEYWORDS)
    sensitivity_ok = as_bool(evidence.get("sensitivity_analysis")) or any("sensitivity" in p.name.lower() or "敏感" in p.name for p in result_tables + code_files)
    comparison_ok = as_bool(evidence.get("model_comparison")) or any(re.search(r"(compare|comparison|baseline|对比|基线)", p.name, re.I) for p in result_tables + figures)
    simulation_ok = as_bool(evidence.get("simulation")) or any(re.search(r"(simulation|monte|risk|robust|鲁棒|风险|情景)", p.name, re.I) for p in result_tables + figures + code_files)

    checks.append(Check(
        "baseline_or_model_comparison", "competition", "pass" if comparison_ok else "warn",
        "存在 baseline/模型对比证据" if comparison_ok else "缺少 baseline 或替代模型对比，论文说服力不足",
    ))
    checks.append(Check(
        "sensitivity_or_robustness", "competition", "pass" if sensitivity_ok or validation_hits >= 3 else "warn",
        "存在敏感性/鲁棒性/误差检验证据" if sensitivity_ok or validation_hits >= 3 else "缺少敏感性、鲁棒性或误差分析",
        f"validation_keyword_hits={validation_hits}",
    ))
    checks.append(Check(
        "uncertainty_or_risk_evidence", "competition", "pass" if simulation_ok else "warn",
        "存在不确定性/风险/情景分析证据" if simulation_ok else "缺少不确定性或风险分析；若题目不涉及随机性可在 competition_evidence.json 中说明豁免",
    ))
    checks.append(Check(
        "paper_assets", "competition", "pass" if len(figures) >= 3 and len(result_tables) >= 3 else "warn",
        "图表/结果表数量基本支撑论文" if len(figures) >= 3 and len(result_tables) >= 3 else "论文资产偏少：建议补关键结果表、对比图、敏感性图、流程图",
        f"figures={len(figures)}, tables={len(result_tables)}",
    ))

    audit_counts = audit.get("counts", {}) if isinstance(audit, dict) else {}
    repair_ready = repair.get("delivery_readiness") if isinstance(repair, dict) else None
    if audit_counts:
        checks.append(Check(
            "report_result_consistency", "competition", "pass" if int(audit_counts.get("fail", 0) or 0) == 0 else "fail",
            f"报告-结果一致性 fail={audit_counts.get('fail', 0)}, warn={audit_counts.get('warn', 0)}",
            "06_过程记录/一致性检查/auto_report_audit.json",
        ))
    if repair_ready:
        checks.append(Check(
            "delivery_repair_readiness", "competition", "pass" if repair_ready == "ready" else "warn",
            f"repair_advisor delivery_readiness={repair_ready}",
            "06_过程记录/修复建议/repair_advice.json",
        ))

    counts: dict[str, dict[str, int]] = {}
    for level in ["workflow", "model", "competition"]:
        level_checks = [c for c in checks if c.level == level]
        counts[level] = {
            "pass": sum(c.status == "pass" for c in level_checks),
            "warn": sum(c.status == "warn" for c in level_checks),
            "fail": sum(c.status == "fail" for c in level_checks),
            "total": len(level_checks),
        }

    if counts["workflow"]["fail"] == 0:
        workflow_ready = True
    else:
        workflow_ready = False
    model_ready = workflow_ready and counts["model"]["fail"] == 0 and counts["model"]["warn"] <= 1
    competition_ready = model_ready and counts["competition"]["fail"] == 0 and counts["competition"]["warn"] <= 1

    if not workflow_ready:
        readiness = "workflow_blocked"
    elif not model_ready:
        readiness = "model_not_ready"
    elif not competition_ready:
        readiness = "competition_needs_review"
    else:
        readiness = "competition_ready"

    summary = {
        "readiness": readiness,
        "workflow_ready": workflow_ready,
        "model_ready": model_ready,
        "competition_ready": competition_ready,
        "counts": counts,
        "evidence_file": evidence.get("_path", ""),
        "checks": [asdict(c) for c in checks],
    }
    return summary


def write_outputs(project: Path, summary: dict[str, Any]) -> tuple[Path, Path]:
    out_dir = project / "06_过程记录" / "竞赛就绪度"
    out_dir.mkdir(parents=True, exist_ok=True)
    json_path = out_dir / "competition_readiness.json"
    md_path = out_dir / "competition_readiness.md"
    json_path.write_text(json.dumps(summary, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    lines = ["# 数学建模竞赛就绪度评估\n\n"]
    lines.append(f"- readiness：**{summary['readiness']}**\n")
    lines.append(f"- workflow_ready：{summary['workflow_ready']}\n")
    lines.append(f"- model_ready：{summary['model_ready']}\n")
    lines.append(f"- competition_ready：{summary['competition_ready']}\n")
    if summary.get("evidence_file"):
        lines.append(f"- competition_evidence：`{summary['evidence_file']}`\n")
    lines.append("\n## 分层统计\n\n")
    lines.append("| 层级 | pass | warn | fail | total |\n|---|---:|---:|---:|---:|\n")
    for level, c in summary["counts"].items():
        lines.append(f"| {level} | {c['pass']} | {c['warn']} | {c['fail']} | {c['total']} |\n")
    lines.append("\n## 检查项\n\n")
    lines.append("| 层级 | 检查项 | 状态 | 说明 | 证据 |\n|---|---|---|---|---|\n")
    icon = {"pass": "✅ pass", "warn": "⚠️ warn", "fail": "❌ fail"}
    for ch in summary["checks"]:
        evidence = str(ch.get("evidence", "")).replace("|", "/")[:180]
        msg = str(ch.get("message", "")).replace("|", "/")
        lines.append(f"| {ch['level']} | {ch['id']} | {icon.get(ch['status'], ch['status'])} | {msg} | {evidence} |\n")
    lines.append("\n## 口径说明\n\n")
    lines.append("`competition_ready` 不是保证获奖，只表示：工程闭环、正式模型证据、逐问覆盖、验证/对比/风险分析和论文资产达到可参赛评审口径。若为 `competition_needs_review`，优先补 warn 项。\n")
    md_path.write_text("".join(lines), encoding="utf-8")
    return json_path, md_path


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("project")
    parser.add_argument("--strict", action="store_true", help="exit non-zero unless competition_ready")
    args = parser.parse_args()
    project = Path(args.project).expanduser().resolve()
    if not project.exists():
        print(f"Project not found: {project}", file=sys.stderr)
        return 2
    summary = assess(project)
    json_path, md_path = write_outputs(project, summary)
    print(f"Competition readiness: {summary['readiness']}")
    print(f"Report: {md_path}")
    print(f"JSON: {json_path}")
    if args.strict and not summary["competition_ready"]:
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
