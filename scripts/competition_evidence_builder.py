#!/usr/bin/env python3
"""Build a generic competition_evidence.json for mathematical modeling projects.

This script does not certify model correctness. It collects explicit, reviewable
evidence from project artifacts so `competition_readiness_gate.py` can judge
competition readiness without relying only on brittle keyword scanning.
"""
from __future__ import annotations

import argparse
import csv
import json
import re
import zipfile
from pathlib import Path
from typing import Any

TABLE_EXTS = {".csv", ".xlsx", ".xls", ".json"}
FIG_EXTS = {".png", ".jpg", ".jpeg", ".svg", ".pdf"}
CODE_EXTS = {".py", ".ipynb", ".m", ".r"}
REPORT_EXTS = {".md", ".tex", ".docx", ".pdf"}
PLACEHOLDER_PATTERNS = [r"placeholder", r"baseline-derived", r"TODO", r"待补充", r"待完成", r"仅用于链路测试", r"replace with problem-specific"]
MODEL_PATTERNS = [r"目标函数", r"约束", r"决策变量", r"变量定义", r"MIP|MILP|LP|NLP", r"整数规划", r"线性规划", r"动态规划", r"Monte Carlo|蒙特卡洛", r"回归", r"预测", r"TOPSIS|AHP|熵权", r"仿真", r"网络流|VRP|TSP", r"鲁棒"]
CHECKER_PATTERNS = [r"check", r"checker", r"validate", r"verify", r"constraint", r"quality", r"gate", r"audit", r"可行", r"约束", r"检查"]
SOLVER_PATTERNS = [r"solve", r"solver", r"optimi", r"pulp", r"ortools", r"cvxpy", r"scipy\.optimize", r"linprog", r"milp", r"求解", r"优化"]
SIM_PATTERNS = [r"simulation", r"simulate", r"monte", r"scenario", r"risk", r"robust", r"bootstrap", r"情景", r"风险", r"鲁棒", r"仿真"]
SENS_PATTERNS = [r"sensitivity", r"robust", r"perturb", r"ablation", r"敏感", r"鲁棒", r"扰动", r"消融"]
COMPARE_PATTERNS = [r"baseline", r"compare", r"comparison", r"benchmark", r"基线", r"对比", r"比较"]
OFFICIAL_RESULT_PATTERNS = [r"^result\d*", r"结果\d*", r"提交", r"template", r"模板"]


def list_files(root: Path, exts: set[str] | None = None) -> list[Path]:
    if not root.exists():
        return []
    files = [p for p in root.rglob("*") if p.is_file() and not p.name.startswith("~$")]
    if exts:
        files = [p for p in files if p.suffix.lower() in exts]
    return sorted(files)


def rel(project: Path, path: Path) -> str:
    try:
        return str(path.relative_to(project))
    except Exception:
        return str(path)


def read_text(path: Path, limit: int = 500_000) -> str:
    try:
        if path.suffix.lower() == ".docx":
            import xml.etree.ElementTree as ET
            with zipfile.ZipFile(path) as z:
                xml = z.read("word/document.xml")
            root = ET.fromstring(xml)
            return "\n".join(node.text or "" for node in root.iter() if node.tag.endswith("}t"))[:limit]
        if path.suffix.lower() in {".pdf", ".xlsx", ".xls", ".ipynb"}:
            if path.suffix.lower() == ".ipynb":
                return path.read_text(encoding="utf-8", errors="ignore")[:limit]
            return ""
        return path.read_text(encoding="utf-8", errors="ignore")[:limit]
    except Exception:
        return ""


def csv_has_data(path: Path) -> bool:
    try:
        with path.open("r", encoding="utf-8-sig", errors="ignore", newline="") as f:
            rows = list(csv.reader(f))
        return len(rows) > 1 and any(any(str(x).strip() for x in row) for row in rows[1:])
    except Exception:
        return False


def json_load(path: Path) -> dict[str, Any]:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return {}


def count_hits(text: str, patterns: list[str]) -> int:
    return sum(1 for pat in patterns if re.search(pat, text, flags=re.I))


def grep_files(files: list[Path], patterns: list[str]) -> list[Path]:
    out = []
    for p in files:
        name_hit = any(re.search(pat, p.name, flags=re.I) for pat in patterns)
        text_hit = False
        if p.suffix.lower() in CODE_EXTS | {".md", ".tex", ".json"}:
            text_hit = count_hits(read_text(p, 200_000), patterns) > 0
        if name_hit or text_hit:
            out.append(p)
    return out


def infer_checker_issue_count(project: Path, checker_files: list[Path]) -> int | None:
    """Infer issue_count from known project JSON/MD artifacts if present."""
    candidates = []
    for root in [project / "06_过程记录", project / "03_结果表格"]:
        candidates.extend(list_files(root, {".json", ".md", ".csv"}))
    for p in candidates:
        text = read_text(p, 300_000)
        m = re.search(r"issue_count['\"：:=\s]+(\d+)", text, flags=re.I)
        if m:
            return int(m.group(1))
        m = re.search(r"问题数['\"：:=\s]+(\d+)", text)
        if m:
            return int(m.group(1))
    # If explicit checker script exists but no count, return None rather than pretending zero.
    return None




def load_domain_checker_templates(project: Path) -> dict[str, Any]:
    """Read generated domain-checker template index if present."""
    return json_load(project / "06_过程记录" / "领域checker" / "domain_checker_templates.json")


def detect_domain_checker_implementation(project: Path, checker_files: list[Path]) -> dict[str, Any]:
    """Classify checker evidence into template_only / implemented_warn / implemented_pass.

    Generated checker templates are useful scaffolding, but they are not formal
    model evidence until project-specific TODO checks are replaced and an output
    JSON/MD reports issue_count=0 with no TODO/warn leftovers.
    """
    template_index = load_domain_checker_templates(project)
    template_files = set()
    if isinstance(template_index, dict):
        for x in template_index.get("checker_files", []) or []:
            template_files.add(str(x))

    output_candidates = []
    # Only formal checker outputs should influence implementation status. Avoid
    # accidental issue_count strings in model_skeleton/pipeline summaries.
    output_candidates.extend(list_files(project / "06_过程记录" / "领域checker", {".json", ".md"}))
    output_candidates.extend([p for p in list_files(project / "03_结果表格", {".json", ".md"}) if re.search(r"checker|constraint|validate|feasibility|约束|可行", p.name, flags=re.I)])

    outputs: list[dict[str, Any]] = []
    best_issue_count: int | None = None
    warn_count_total = 0
    todo_hits_total = 0
    for p in output_candidates:
        text = read_text(p, 300_000)
        if p.name == "domain_checker_templates.json" or p.name == "domain_checker_templates.md":
            # Template index proves only template existence, not implementation.
            continue
        if not re.search(r"domain_checker|领域\s*checker|checker_type", text, flags=re.I):
            continue
        issue = None
        data = json_load(p) if p.suffix.lower() == ".json" else {}
        if isinstance(data, dict) and "issue_count" in data:
            try:
                issue = int(data.get("issue_count"))
            except Exception:
                issue = None
            try:
                warn_count_total += int(data.get("warn_count", 0) or 0)
            except Exception:
                pass
        if issue is None:
            m = re.search(r"issue_count['\"：:=\s]+(\d+)", text, flags=re.I)
            if m:
                issue = int(m.group(1))
        todo_hits = count_hits(text, [r"TODO", r"template requires project-specific", r"模板", r"starter"])
        todo_hits_total += todo_hits
        if issue is not None:
            best_issue_count = issue if best_issue_count is None else min(best_issue_count, issue)
        outputs.append({"path": rel(project, p), "issue_count": issue, "todo_hits": todo_hits})

    generated_checker_files = []
    implemented_checker_files = []
    for p in checker_files:
        rp = rel(project, p)
        text = read_text(p, 200_000)
        is_generated = "generated_checkers" in rp or "generated_skeleton" in rp or rp in template_files or "template requires project-specific" in text or "TODO:" in text
        if is_generated:
            generated_checker_files.append(rp)
        else:
            implemented_checker_files.append(rp)

    has_templates = bool(template_files or generated_checker_files or template_index)
    has_outputs = bool(outputs)
    # Generated starters may coexist with an independent, project-specific checker.
    # Only unresolved markers in formal checker outputs can downgrade that output.
    has_todo = todo_hits_total > 0

    if has_outputs and best_issue_count == 0 and not has_todo and warn_count_total == 0:
        status = "implemented_checker_pass"
    elif has_outputs and best_issue_count is not None:
        status = "implemented_checker_warn" if best_issue_count == 0 else "implemented_checker_fail"
    elif has_templates:
        status = "template_checker_only"
    elif checker_files:
        status = "checker_detected_no_machine_output"
    else:
        status = "not_detected"

    return {
        "status": status,
        "template_index_detected": bool(template_index),
        "generated_checker_files": generated_checker_files[:12],
        "implemented_checker_files": implemented_checker_files[:12],
        "outputs": outputs[:12],
        "issue_count": best_issue_count,
        "warn_count": warn_count_total,
        "todo_hits": todo_hits_total,
    }


def build(project: Path) -> dict[str, Any]:
    raw = list_files(project / "00_题目与资料") + list_files(project / "01_原始数据")
    code = list_files(project / "02_代码", CODE_EXTS)
    tables = list_files(project / "03_结果表格", TABLE_EXTS)
    figures = list_files(project / "04_图表", FIG_EXTS)
    reports = list_files(project / "05_报告定稿", REPORT_EXTS)
    process_docs = list_files(project / "06_过程记录", {".md", ".json"})

    combined_text = "\n".join(read_text(p, 200_000) for p in code + reports + process_docs)
    placeholder_hits = count_hits(combined_text, PLACEHOLDER_PATTERNS)
    model_hits = count_hits(combined_text, MODEL_PATTERNS)

    model_files = grep_files(code + process_docs, MODEL_PATTERNS + SOLVER_PATTERNS)
    checker_files = grep_files(code + process_docs, CHECKER_PATTERNS)
    solver_files = grep_files(code, SOLVER_PATTERNS)
    simulation_files = grep_files(code + tables + figures + process_docs, SIM_PATTERNS)
    sensitivity_files = grep_files(code + tables + figures + process_docs, SENS_PATTERNS)
    comparison_files = grep_files(code + tables + figures + process_docs, COMPARE_PATTERNS)
    official_outputs = [p for p in tables if any(re.search(pat, p.stem, flags=re.I) for pat in OFFICIAL_RESULT_PATTERNS)]
    nonempty_csvs = [p for p in tables if p.suffix.lower() != ".csv" or csv_has_data(p)]

    quality = json_load(project / "06_过程记录" / "质量门禁" / "quality_gate_plus.json")
    coverage = json_load(project / "06_过程记录" / "问题覆盖" / "problem_coverage.json")
    audit = json_load(project / "06_过程记录" / "一致性检查" / "auto_report_audit.json")
    repair = json_load(project / "06_过程记录" / "修复建议" / "repair_advice.json")
    contest_qc = json_load(project / "06_过程记录" / "竞赛质控" / "contest_qc_gate.json")

    issue_count = infer_checker_issue_count(project, checker_files)
    checker_implementation = detect_domain_checker_implementation(project, checker_files)
    formal_checker_pass = checker_implementation.get("status") == "implemented_checker_pass"
    domain_checker: dict[str, Any] = {
        "detected": bool(checker_files) or checker_implementation.get("status") != "not_detected",
        "paths": [rel(project, p) for p in checker_files[:12]],
        "implementation": checker_implementation,
    }
    if formal_checker_pass:
        domain_checker["issue_count"] = 0
        domain_checker["status"] = "pass"
    elif checker_implementation.get("status") in {"template_checker_only", "implemented_checker_warn", "checker_detected_no_machine_output"}:
        domain_checker["status"] = checker_implementation.get("status")
        if checker_implementation.get("issue_count") is not None:
            domain_checker["issue_count"] = checker_implementation.get("issue_count")
        domain_checker["note"] = "checker exists but is not yet formal pass evidence; replace generated TODO checks and produce issue_count=0 with warn_count=0."
    elif issue_count is not None:
        domain_checker["issue_count"] = issue_count
        domain_checker["status"] = "pass" if issue_count == 0 else "fail"
    else:
        domain_checker["status"] = "unknown" if checker_files else "not_detected"
        domain_checker["note"] = "checker-like artifacts detected but no formal issue_count found; add explicit issue_count for strict readiness."

    evidence: dict[str, Any] = {
        "schema_version": "1.0",
        "generated_by": "competition_evidence_builder.py",
        "project": str(project),
        "artifact_counts": {
            "raw_materials": len(raw),
            "code_files": len(code),
            "result_tables": len(tables),
            "nonempty_result_tables": len(nonempty_csvs),
            "figures": len(figures),
            "reports": len(reports),
        },
        "problem_specific_model": {
            "status": bool(model_files and model_hits >= 3 and placeholder_hits == 0),
            "model_keyword_hits": model_hits,
            "placeholder_hits": placeholder_hits,
            "paths": [rel(project, p) for p in model_files[:12]],
            "note": "status=false when placeholder/TODO/link-test language remains, even if model keywords exist.",
        },
        "domain_checker": domain_checker,
        "official_templates_filled": [rel(project, p) for p in official_outputs],
        "optimization_solver": {
            "detected": bool(solver_files),
            "paths": [rel(project, p) for p in solver_files[:12]],
            "status": "detected" if solver_files else "not_detected",
        },
        "simulation": {
            "detected": bool(simulation_files),
            "paths": [rel(project, p) for p in simulation_files[:12]],
        },
        "model_comparison": {
            "detected": bool(comparison_files),
            "paths": [rel(project, p) for p in comparison_files[:12]],
        },
        "sensitivity_analysis": {
            "detected": bool(sensitivity_files),
            "paths": [rel(project, p) for p in sensitivity_files[:12]],
        },
        "paper_assets": {
            "figures": len(figures),
            "tables": len(tables),
            "reports": [rel(project, p) for p in reports[:8]],
        },
        "upstream_audits": {
            "quality_gate_plus_counts": quality.get("counts", {}) if isinstance(quality, dict) else {},
            "problem_coverage_counts": coverage.get("counts", {}) if isinstance(coverage, dict) else {},
            "report_audit_counts": audit.get("counts", {}) if isinstance(audit, dict) else {},
            "repair_delivery_readiness": repair.get("delivery_readiness") if isinstance(repair, dict) else None,
        },
        "contest_qc": {
            "path": "06_过程记录/竞赛质控/contest_qc_gate.json" if contest_qc else "",
            "phase": contest_qc.get("phase") if isinstance(contest_qc, dict) else None,
            "readiness": contest_qc.get("readiness") if isinstance(contest_qc, dict) else None,
            "counts": contest_qc.get("counts", {}) if isinstance(contest_qc, dict) else {},
        },
        "review_notes": [],
    }

    if placeholder_hits:
        evidence["review_notes"].append("Placeholder/TODO/link-test language remains; replace generic baseline with problem-specific final model or move old artifacts out of final scope.")
    qc_readiness = evidence["contest_qc"].get("readiness")
    if qc_readiness == "blocked":
        evidence["review_notes"].append("Contest QC has hard evidence blockers; inspect 06_过程记录/竞赛质控/contest_qc_gate.md before promoting paper claims.")
    elif qc_readiness == "needs_review":
        evidence["review_notes"].append("Contest QC has no hard block but needs review evidence; clear the remaining warnings before final submission.")
    elif not qc_readiness:
        evidence["review_notes"].append("Contest QC evidence is absent; run contest_qc_gate.py before final competition-readiness assessment.")
    checker_status = evidence["domain_checker"].get("status")
    if checker_status in {"not_detected", "unknown"}:
        evidence["review_notes"].append("No formal domain-specific checker pass detected; add a feasibility/constraint checker for the chosen problem type.")
    elif checker_status == "template_checker_only":
        evidence["review_notes"].append("Only generated checker templates detected; replace TODO checks with project-specific executable hard constraints before claiming model_ready.")
    elif checker_status == "implemented_checker_warn":
        evidence["review_notes"].append("Checker output exists but still has warn/TODO evidence; resolve warnings or justify them before competition_ready.")
    elif checker_status == "implemented_checker_fail":
        evidence["review_notes"].append("Checker output reports issue_count>0; fix hard-constraint violations before submission.")
    if len(figures) < 3:
        evidence["review_notes"].append("Figure assets are thin for award-oriented report; add result comparison, sensitivity/robustness and model-flow figures.")
    if not simulation_files:
        evidence["review_notes"].append("No risk/simulation/uncertainty evidence detected; if the problem is deterministic, document why this is not needed.")

    return evidence


def write_markdown(project: Path, evidence: dict[str, Any]) -> Path:
    out = project / "06_过程记录" / "competition_evidence.md"
    lines = ["# 竞赛证据自动汇总\n\n"]
    lines.append("本文件由 `competition_evidence_builder.py` 生成；它是就绪度门禁的证据索引，不等于模型正确性证明。\n\n")
    lines.append("## 产物统计\n\n")
    lines.append("| 项 | 数量 |\n|---|---:|\n")
    for k, v in evidence["artifact_counts"].items():
        lines.append(f"| {k} | {v} |\n")
    lines.append("\n## 核心证据\n\n")
    lines.append(f"- problem_specific_model.status: `{evidence['problem_specific_model']['status']}`\n")
    lines.append(f"- model_keyword_hits: `{evidence['problem_specific_model']['model_keyword_hits']}`\n")
    lines.append(f"- placeholder_hits: `{evidence['problem_specific_model']['placeholder_hits']}`\n")
    lines.append(f"- domain_checker.status: `{evidence['domain_checker']['status']}`\n")
    if "issue_count" in evidence["domain_checker"]:
        lines.append(f"- domain_checker.issue_count: `{evidence['domain_checker']['issue_count']}`\n")
    lines.append(f"- optimization_solver.detected: `{evidence['optimization_solver']['detected']}`\n")
    lines.append(f"- simulation.detected: `{evidence['simulation']['detected']}`\n")
    lines.append(f"- model_comparison.detected: `{evidence['model_comparison']['detected']}`\n")
    lines.append(f"- sensitivity_analysis.detected: `{evidence['sensitivity_analysis']['detected']}`\n")
    lines.append(f"- contest_qc.readiness: `{evidence['contest_qc']['readiness']}`\n")
    lines.append("\n## Review notes\n\n")
    if evidence["review_notes"]:
        for note in evidence["review_notes"]:
            lines.append(f"- {note}\n")
    else:
        lines.append("- 未发现自动证据层面的明显阻塞；仍需人工核验题意和模型正确性。\n")
    out.write_text("".join(lines), encoding="utf-8")
    return out


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("project")
    parser.add_argument("--strict", action="store_true", help="exit non-zero if blocking evidence issues remain")
    args = parser.parse_args()
    project = Path(args.project).expanduser().resolve()
    if not project.exists():
        print(f"Project not found: {project}")
        return 2
    evidence = build(project)
    out_json = project / "06_过程记录" / "competition_evidence.json"
    out_json.parent.mkdir(parents=True, exist_ok=True)
    out_json.write_text(json.dumps(evidence, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    out_md = write_markdown(project, evidence)
    print(f"Competition evidence: {out_json}")
    print(f"Evidence markdown: {out_md}")
    print(f"problem_specific_model={evidence['problem_specific_model']['status']} placeholder_hits={evidence['problem_specific_model']['placeholder_hits']} domain_checker={evidence['domain_checker']['status']}")
    if args.strict:
        blocking = evidence["problem_specific_model"]["placeholder_hits"] > 0 or evidence["domain_checker"].get("status") not in {"pass"}
        if blocking:
            return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
