#!/usr/bin/env python3
"""Run an end-to-end control pipeline for mathematical modeling projects.

This script orchestrates the existing project-level checks without deleting data:
  1) optional data audit:              02_代码/00_data_audit.py
  2) optional model skeleton routing:   model_skeleton_router.py
  3) optional quality gate:            02_代码/06_quality_gate.py
  3) report-result consistency audit:  audit_report_consistency.py
  4) state updater:                    update_project_state.py
  5) final package builder:            finalize_modeling_project.py
  6) enhanced quality gate:            quality_gate_plus.py
  7) per-question coverage tracker:    problem_coverage_tracker.py
  8) result interpretation helper:      result_interpretation_helper.py

It writes:
  06_过程记录/pipeline/pipeline_run_summary.json
  06_过程记录/pipeline/pipeline_run_summary.md

The pipeline proves workflow closure, not model correctness.
"""
from __future__ import annotations

import argparse
import json
import shlex
import subprocess
import sys
import time
from dataclasses import asdict, dataclass
from datetime import datetime
from pathlib import Path

SKILL_DIR = Path(__file__).resolve().parents[1]
AUDIT_SCRIPT = SKILL_DIR / "scripts" / "audit_report_consistency.py"
STATE_SCRIPT = SKILL_DIR / "scripts" / "update_project_state.py"
FINALIZE_SCRIPT = SKILL_DIR / "scripts" / "finalize_modeling_project.py"
QUALITY_PLUS_SCRIPT = SKILL_DIR / "scripts" / "quality_gate_plus.py"
COVERAGE_SCRIPT = SKILL_DIR / "scripts" / "problem_coverage_tracker.py"
INTERPRET_SCRIPT = SKILL_DIR / "scripts" / "result_interpretation_helper.py"
ASSEMBLER_SCRIPT = SKILL_DIR / "scripts" / "report_section_assembler.py"
REPAIR_SCRIPT = SKILL_DIR / "scripts" / "repair_advisor.py"
COMPETITION_SCRIPT = SKILL_DIR / "scripts" / "competition_readiness_gate.py"
EVIDENCE_SCRIPT = SKILL_DIR / "scripts" / "competition_evidence_builder.py"
SKELETON_SCRIPT = SKILL_DIR / "scripts" / "model_skeleton_router.py"
DOMAIN_CHECKER_TEMPLATE_SCRIPT = SKILL_DIR / "scripts" / "domain_checker_template_builder.py"
CONTEST_QC_SCRIPT = SKILL_DIR / "scripts" / "contest_qc_gate.py"
CONTEST_EVIDENCE_SYNC_SCRIPT = SKILL_DIR / "scripts" / "contest_evidence_sync.py"


@dataclass
class StepResult:
    name: str
    command: list[str]
    exit_code: int
    duration_sec: float
    stdout_tail: str
    stderr_tail: str
    skipped: bool = False
    reason: str = ""


def tail_text(text: str, limit: int = 4000) -> str:
    if len(text) <= limit:
        return text
    return text[-limit:]


def run_command(name: str, command: list[str], cwd: Path, timeout: int = 600) -> StepResult:
    start = time.time()
    try:
        proc = subprocess.run(
            command,
            cwd=str(cwd),
            text=True,
            capture_output=True,
            timeout=timeout,
        )
        return StepResult(
            name=name,
            command=command,
            exit_code=proc.returncode,
            duration_sec=round(time.time() - start, 3),
            stdout_tail=tail_text(proc.stdout),
            stderr_tail=tail_text(proc.stderr),
        )
    except subprocess.TimeoutExpired as e:
        return StepResult(
            name=name,
            command=command,
            exit_code=124,
            duration_sec=round(time.time() - start, 3),
            stdout_tail=tail_text(e.stdout or ""),
            stderr_tail=tail_text((e.stderr or "") + f"\nTIMEOUT after {timeout}s"),
        )


def skipped_step(name: str, command: list[str], reason: str) -> StepResult:
    return StepResult(name=name, command=command, exit_code=0, duration_sec=0.0, stdout_tail="", stderr_tail="", skipped=True, reason=reason)


def read_json(path: Path) -> dict:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return {}


def status_from_steps(
    steps: list[StepResult],
    highest_contiguous_state: str | None,
    skeleton_only: bool,
    *,
    current_package_published: bool = False,
    finalize_blocked: bool = False,
) -> tuple[str, int, int]:
    """Report step health without overstating project completion.

    A zero exit status only proves that the selected pipeline steps ran.  It does
    not prove a complete S0-S8 project, especially in --skeleton-only mode.
    """
    failures = sum(1 for s in steps if not s.skipped and s.exit_code != 0)
    warnings = 0
    if failures:
        return "failed", failures, warnings
    if skeleton_only:
        return "early_stage_passed", failures, warnings
    if finalize_blocked:
        return "blocked", failures, warnings
    if current_package_published and highest_contiguous_state == "S8":
        return "completed", failures, warnings
    return "in_progress", failures, warnings


def pipeline_step_names(skeleton_only: bool) -> list[str]:
    early = [
        "data_audit",
        "model_skeleton",
        "domain_checker_templates",
        "quality_gate",
    ]
    if skeleton_only:
        return early + ["state_update_pre_finalize"]
    return early + [
        "quality_gate_plus",
        "problem_coverage",
        "result_interpretation",
        "report_assembly",
        "report_audit",
        "state_update_pre_finalize",
        "contest_evidence_sync",
        "contest_qc",
        "competition_evidence",
        "repair_advisor",
        "competition_readiness",
        "finalize",
        "state_update_final",
    ]


def write_summary(project: Path, summary: dict) -> tuple[Path, Path]:
    out_dir = project / "06_过程记录" / "pipeline"
    out_dir.mkdir(parents=True, exist_ok=True)
    json_path = out_dir / "pipeline_run_summary.json"
    md_path = out_dir / "pipeline_run_summary.md"
    json_path.write_text(json.dumps(summary, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    lines: list[str] = []
    lines.append("# 建模项目总控 Pipeline 运行摘要\n\n")
    lines.append(f"生成时间：{summary['generated_at']}\n\n")
    lines.append(f"项目：`{summary['project']}`\n\n")
    lines.append(f"推荐状态：**{summary['recommended_status']}**\n\n")
    lines.append(f"最高连续状态：`{summary.get('highest_contiguous_state', 'unknown')}`\n\n")
    lines.append(f"本轮已发布当前提交包：`{summary.get('current_package_published', False)}`\n\n")
    lines.append("## 步骤结果\n\n")
    lines.append("| 步骤 | 状态 | exit_code | 用时(s) | 命令/说明 |\n|---|---|---:|---:|---|\n")
    for s in summary["steps"]:
        if s["skipped"]:
            mark = "⏭️ skipped"
            detail = s["reason"]
        elif s["exit_code"] == 0:
            mark = "✅ pass"
            detail = "`" + " ".join(shlex.quote(x) for x in s["command"]) + "`"
        else:
            mark = "❌ fail"
            detail = "`" + " ".join(shlex.quote(x) for x in s["command"]) + "`"
        lines.append(f"| {s['name']} | {mark} | {s['exit_code']} | {s['duration_sec']} | {detail} |\n")

    lines.append("\n## 审计摘要\n\n")
    audit_counts = summary.get("audit_counts") or {}
    quality_plus_counts = summary.get("quality_plus_counts") or {}
    coverage_counts = summary.get("coverage_counts") or {}
    interpretation_counts = summary.get("interpretation_counts") or {}
    assembly_counts = summary.get("assembly_counts") or {}
    evidence_sync_counts = summary.get("evidence_sync_counts") or {}
    contest_qc_counts = summary.get("contest_qc_counts") or {}
    repair_counts = summary.get("repair_counts") or {}
    competition_counts = summary.get("competition_counts") or {}
    model_skeleton_summary = summary.get("model_skeleton") or {}
    domain_checker_templates_summary = summary.get("domain_checker_templates") or {}
    finalize_counts = summary.get("finalize_counts") or {}
    lines.append(f"- 模型骨架路由：primary={model_skeleton_summary.get('primary_type', 'NA')} confidence={model_skeleton_summary.get('primary_confidence', 'NA')} routes={model_skeleton_summary.get('route_count', 'NA')}\n")
    lines.append(f"- 领域checker模板：types={domain_checker_templates_summary.get('checker_types', 'NA')} files={domain_checker_templates_summary.get('checker_file_count', 'NA')}\n")
    lines.append(f"- 报告一致性审计：pass={audit_counts.get('pass', 'NA')} warn={audit_counts.get('warn', 'NA')} fail={audit_counts.get('fail', 'NA')}\n")
    lines.append(f"- 增强质量门禁：pass={quality_plus_counts.get('pass', 'NA')} warn={quality_plus_counts.get('warn', 'NA')} fail={quality_plus_counts.get('fail', 'NA')}\n")
    lines.append(f"- 问题覆盖追踪：questions={coverage_counts.get('questions', 'NA')} missing={coverage_counts.get('missing_questions', 'NA')} weak_assets={coverage_counts.get('weak_asset_questions', 'NA')} warn={coverage_counts.get('warn', 'NA')} fail={coverage_counts.get('fail', 'NA')}\n")
    lines.append(f"- 结果解释草稿：questions={interpretation_counts.get('questions', 'NA')} without_tables={interpretation_counts.get('drafts_without_tables', 'NA')} warn={interpretation_counts.get('warn', 'NA')} fail={interpretation_counts.get('fail', 'NA')}\n")
    lines.append(f"- 报告骨架拼装：questions={assembly_counts.get('questions', 'NA')} ready={assembly_counts.get('ready_sections', 'NA')} partial={assembly_counts.get('partial_sections', 'NA')} weak={assembly_counts.get('weak_sections', 'NA')} warn={assembly_counts.get('warn', 'NA')} fail={assembly_counts.get('fail', 'NA')}\n")
    lines.append(f"- 证据候选同步：status={summary.get('evidence_sync_status', 'NA')} discovered={evidence_sync_counts.get('discovered', 'NA')} added={evidence_sync_counts.get('added', 'NA')} updated={evidence_sync_counts.get('updated', 'NA')} conflicts={evidence_sync_counts.get('conflicts', 'NA')}\n")
    lines.append(f"- 竞赛质控：readiness={summary.get('contest_qc_readiness', 'NA')} pass={contest_qc_counts.get('pass', 'NA')} warn={contest_qc_counts.get('warn', 'NA')} fail={contest_qc_counts.get('fail', 'NA')}\n")
    lines.append(f"- 修复建议：delivery_readiness={summary.get('delivery_readiness', 'NA')} advice={repair_counts.get('advice_items', 'NA')} warn={repair_counts.get('warn', 'NA')} fail={repair_counts.get('fail', 'NA')}\n")
    lines.append(f"- 竞赛就绪度：readiness={summary.get('competition_readiness', 'NA')} workflow_fail={competition_counts.get('workflow', {}).get('fail', 'NA')} model_fail={competition_counts.get('model', {}).get('fail', 'NA')} competition_warn={competition_counts.get('competition', {}).get('warn', 'NA')} competition_fail={competition_counts.get('competition', {}).get('fail', 'NA')}\n")
    lines.append(f"- 最终打包检查：warn={finalize_counts.get('warn', 'NA')} fail={finalize_counts.get('fail', 'NA')}\n")
    if summary.get("final_package"):
        lines.append(f"- 提交包目录：`{summary['final_package']}`\n")
    lines.append("\n## 失败/警告定位\n\n")
    any_detail = False
    for s in summary["steps"]:
        if not s["skipped"] and s["exit_code"] != 0:
            any_detail = True
            lines.append(f"### {s['name']}\n\n")
            if s.get("stdout_tail"):
                lines.append("stdout tail:\n\n```text\n" + s["stdout_tail"] + "\n```\n\n")
            if s.get("stderr_tail"):
                lines.append("stderr tail:\n\n```text\n" + s["stderr_tail"] + "\n```\n\n")
    if not any_detail:
        lines.append("未发现失败步骤。\n")
    md_path.write_text("".join(lines), encoding="utf-8")
    return json_path, md_path


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("project", help="Project directory")
    parser.add_argument("--entry", default="02_代码/03_model_main.py", help="Code entry passed to finalize_modeling_project.py")
    parser.add_argument("--report", action="append", default=None, help="Report path relative to project or absolute; can repeat")
    parser.add_argument("--strict", action="store_true", help="Fail on warnings in audit/finalize where supported")
    parser.add_argument("--strict-numbers", action="store_true", help="Fail audit when report numbers do not match result tables")
    parser.add_argument("--zip", action="store_true", help="Ask finalize_modeling_project.py to create submission_package.zip")
    parser.add_argument("--include-raw-data", action="store_true", help="Include raw data in final package if allowed")
    parser.add_argument("--no-code", action="store_true", help="Do not copy code into final package")
    parser.add_argument("--skip-data-audit", action="store_true")
    parser.add_argument("--skip-model-skeleton", action="store_true", help="Skip problem-type routing and model skeleton generation")
    parser.add_argument("--write-model-skeleton-code", action="store_true", help="Also write starter skeleton code under 02_代码/generated_skeleton")
    parser.add_argument("--strict-model-skeleton", action="store_true", help="Fail if model skeleton router has low confidence")
    parser.add_argument("--skip-domain-checker-templates", action="store_true", help="Skip domain checker template generation")
    parser.add_argument("--strict-domain-checker-templates", action="store_true", help="Fail if checker templates cannot be routed from model skeleton")
    parser.add_argument("--domain-checker-max-types", type=int, default=3, help="Maximum routed types to generate checker templates for")
    parser.add_argument("--skip-quality-gate", action="store_true")
    parser.add_argument("--skip-report-audit", action="store_true")
    parser.add_argument("--skip-coverage", action="store_true", help="Skip per-question coverage tracker")
    parser.add_argument("--coverage-min-asset-hits", type=int, default=0, help="Minimum table+figure hits per extracted question; unmet gives warning")
    parser.add_argument("--skip-interpretation", action="store_true", help="Skip result interpretation draft generator")
    parser.add_argument("--strict-interpretation", action="store_true", help="Fail if interpretation draft has warnings")
    parser.add_argument("--skip-report-assembly", action="store_true", help="Skip evidence-first report section assembler")
    parser.add_argument("--strict-report-assembly", action="store_true", help="Fail if report assembly has warnings")
    parser.add_argument("--skip-contest-qc", action="store_true", help="Skip contest evidence/claim/compliance QC gate")
    parser.add_argument("--skip-contest-evidence-sync", action="store_true", help="Skip review-only Contest QC evidence candidate synchronization")
    parser.add_argument("--strict-contest-qc", action="store_true", help="Fail unless the selected contest-QC phase is ready")
    parser.add_argument("--contest-qc-phase", choices=("early", "model", "final"), default="final", help="Contest-QC phase to evaluate")
    parser.add_argument("--report-title", default="数学建模报告", help="Title for assembled report draft")
    parser.add_argument("--report-draft-name", default="report_draft.md", help="Markdown report draft name under 05_报告定稿")
    parser.add_argument("--skip-repair-advisor", action="store_true", help="Skip prioritized repair advice generator")
    parser.add_argument("--strict-repair-advisor", action="store_true", help="Fail if repair advisor says delivery is not ready")
    parser.add_argument("--skip-competition-readiness", action="store_true", help="Skip competition-readiness gate")
    parser.add_argument("--strict-competition-readiness", action="store_true", help="Fail if competition readiness is not competition_ready")
    parser.add_argument("--skip-competition-evidence", action="store_true", help="Skip automatic competition_evidence.json builder")
    parser.add_argument("--strict-competition-evidence", action="store_true", help="Fail if evidence builder detects blocking model/checker evidence issues")
    parser.add_argument("--skip-quality-plus", action="store_true", help="Skip enhanced quality gate")
    parser.add_argument("--skeleton-only", action="store_true", help="Run only data_audit + model_skeleton + quality_gate; useful at S1 before results/report exist")
    parser.add_argument("--skip-finalize", action="store_true")
    parser.add_argument("--timeout", type=int, default=600)
    args = parser.parse_args()

    project = Path(args.project).expanduser().resolve()
    if not project.exists():
        print(f"Project not found: {project}", file=sys.stderr)
        return 2

    py = sys.executable
    steps: list[StepResult] = []

    data_audit = project / "02_代码" / "00_data_audit.py"
    if args.skip_data_audit:
        steps.append(skipped_step("data_audit", [py, str(data_audit)], "--skip-data-audit"))
    elif data_audit.exists():
        steps.append(run_command("data_audit", [py, str(data_audit)], project, timeout=args.timeout))
    else:
        steps.append(skipped_step("data_audit", [py, str(data_audit)], "02_代码/00_data_audit.py not found"))

    if args.skip_model_skeleton:
        steps.append(skipped_step("model_skeleton", [py, str(SKELETON_SCRIPT), str(project)], "--skip-model-skeleton"))
    else:
        cmd = [py, str(SKELETON_SCRIPT), str(project)]
        if args.write_model_skeleton_code:
            cmd.append("--write-code")
        if args.strict_model_skeleton:
            cmd.append("--strict")
        steps.append(run_command("model_skeleton", cmd, project, timeout=args.timeout))

    if args.skip_domain_checker_templates:
        steps.append(skipped_step("domain_checker_templates", [py, str(DOMAIN_CHECKER_TEMPLATE_SCRIPT), str(project)], "--skip-domain-checker-templates"))
    else:
        cmd = [py, str(DOMAIN_CHECKER_TEMPLATE_SCRIPT), str(project), "--max-types", str(args.domain_checker_max_types)]
        if args.strict_domain_checker_templates:
            cmd.append("--strict")
        steps.append(run_command("domain_checker_templates", cmd, project, timeout=args.timeout))

    quality_gate = project / "02_代码" / "06_quality_gate.py"
    if args.skip_quality_gate:
        steps.append(skipped_step("quality_gate", [py, str(quality_gate)], "--skip-quality-gate"))
    elif quality_gate.exists():
        steps.append(run_command("quality_gate", [py, str(quality_gate)], project, timeout=args.timeout))
    else:
        steps.append(skipped_step("quality_gate", [py, str(quality_gate)], "02_代码/06_quality_gate.py not found"))

    if args.skeleton_only:
        args.skip_report_audit = True
        args.skip_finalize = True
        args.skip_quality_plus = True
        args.skip_coverage = True
        args.skip_interpretation = True
        args.skip_report_assembly = True
        args.skip_contest_qc = True
        args.skip_contest_evidence_sync = True
        args.skip_repair_advisor = True
        args.skip_competition_evidence = True
        args.skip_competition_readiness = True

    if args.skip_quality_plus:
        steps.append(skipped_step("quality_gate_plus", [py, str(QUALITY_PLUS_SCRIPT), str(project)], "--skip-quality-plus"))
    else:
        cmd = [py, str(QUALITY_PLUS_SCRIPT), str(project)]
        if args.strict:
            cmd.append("--strict")
        steps.append(run_command("quality_gate_plus", cmd, project, timeout=args.timeout))

    if args.skip_coverage:
        steps.append(skipped_step("problem_coverage", [py, str(COVERAGE_SCRIPT), str(project)], "--skip-coverage"))
    else:
        cmd = [py, str(COVERAGE_SCRIPT), str(project), "--min-asset-hits", str(args.coverage_min_asset_hits)]
        if args.strict:
            cmd.append("--strict")
        steps.append(run_command("problem_coverage", cmd, project, timeout=args.timeout))

    if args.skip_interpretation:
        steps.append(skipped_step("result_interpretation", [py, str(INTERPRET_SCRIPT), str(project)], "--skip-interpretation"))
    else:
        cmd = [py, str(INTERPRET_SCRIPT), str(project)]
        if args.strict_interpretation:
            cmd.append("--strict")
        steps.append(run_command("result_interpretation", cmd, project, timeout=args.timeout))

    if args.skip_report_assembly:
        steps.append(skipped_step("report_assembly", [py, str(ASSEMBLER_SCRIPT), str(project)], "--skip-report-assembly"))
    else:
        cmd = [py, str(ASSEMBLER_SCRIPT), str(project), "--title", args.report_title, "--report-name", args.report_draft_name]
        if args.strict_report_assembly:
            cmd.append("--strict")
        steps.append(run_command("report_assembly", cmd, project, timeout=args.timeout))

    if args.skip_report_audit:
        steps.append(skipped_step("report_audit", [py, str(AUDIT_SCRIPT), str(project)], "--skip-report-audit"))
    else:
        cmd = [py, str(AUDIT_SCRIPT), str(project)]
        for report in args.report or []:
            cmd.extend(["--report", report])
        if args.strict:
            cmd.append("--strict")
        if args.strict_numbers:
            cmd.append("--strict-numbers")
        steps.append(run_command("report_audit", cmd, project, timeout=args.timeout))

    # This state snapshot reflects the latest assembled and audited report.
    steps.append(run_command("state_update_pre_finalize", [py, str(STATE_SCRIPT), str(project)], project, timeout=args.timeout))

    if args.skip_contest_evidence_sync:
        evidence_sync_step = skipped_step(
            "contest_evidence_sync",
            [py, str(CONTEST_EVIDENCE_SYNC_SCRIPT), str(project)],
            "--skip-contest-evidence-sync",
        )
    else:
        evidence_sync_step = run_command(
            "contest_evidence_sync",
            [py, str(CONTEST_EVIDENCE_SYNC_SCRIPT), str(project)],
            project,
            timeout=args.timeout,
        )
    steps.append(evidence_sync_step)

    if not evidence_sync_step.skipped and evidence_sync_step.exit_code != 0:
        steps.append(skipped_step(
            "contest_qc",
            [py, str(CONTEST_QC_SCRIPT), str(project)],
            "contest evidence synchronization failed",
        ))
    elif args.skip_contest_qc:
        steps.append(skipped_step("contest_qc", [py, str(CONTEST_QC_SCRIPT), str(project)], "--skip-contest-qc"))
    else:
        cmd = [py, str(CONTEST_QC_SCRIPT), str(project), "--phase", args.contest_qc_phase]
        if args.strict_contest_qc:
            cmd.append("--strict")
        steps.append(run_command("contest_qc", cmd, project, timeout=args.timeout))

    # Write a preliminary pipeline summary before repair_advisor so it can read step outcomes.
    pre_skeleton_summary = read_json(project / "06_过程记录" / "model_skeleton" / "model_skeleton.json")
    pre_domain_checker_templates = read_json(project / "06_过程记录" / "领域checker" / "domain_checker_templates.json")
    pre_audit_summary = read_json(project / "06_过程记录" / "一致性检查" / "auto_report_audit.json")
    pre_quality_plus_summary = read_json(project / "06_过程记录" / "质量门禁" / "quality_gate_plus.json")
    pre_coverage_summary = read_json(project / "06_过程记录" / "问题覆盖" / "problem_coverage.json")
    pre_interpretation_summary = read_json(project / "06_过程记录" / "结果解释" / "result_interpretation_draft.json")
    pre_assembly_summary = read_json(project / "06_过程记录" / "报告拼装" / "report_section_assembly.json")
    pre_evidence_sync_summary = read_json(project / "06_过程记录" / "竞赛质控" / "evidence_sync.json")
    pre_contest_qc_summary = read_json(project / "06_过程记录" / "竞赛质控" / "contest_qc_gate.json")
    pre_meta = read_json(project / "project_meta.json")
    pre_finalize_checks: list[dict] = []
    pre_summary = {
        "phase": "pre_finalize",
        "generated_at": datetime.now().isoformat(timespec="seconds"),
        "project": str(project),
        "recommended_status": status_from_steps(
            steps, pre_meta.get("highest_contiguous_state"), args.skeleton_only
        )[0],
        "highest_contiguous_state": pre_meta.get("highest_contiguous_state"),
        "current_package_published": False,
        "final_package": "",
        "entry": args.entry,
        "strict": args.strict,
        "strict_numbers": args.strict_numbers,
        "steps": [asdict(s) for s in steps],
        "model_skeleton": {"primary_type": pre_skeleton_summary.get("primary_type"), "primary_confidence": pre_skeleton_summary.get("primary_confidence"), "route_count": len(pre_skeleton_summary.get("routes", []))} if isinstance(pre_skeleton_summary, dict) else {},
        "domain_checker_templates": {"checker_types": ",".join(pre_domain_checker_templates.get("checker_types", [])), "checker_file_count": len(pre_domain_checker_templates.get("checker_files", []))} if isinstance(pre_domain_checker_templates, dict) else {},
        "audit_counts": {} if args.skip_report_audit else (pre_audit_summary.get("counts", {}) if isinstance(pre_audit_summary, dict) else {}),
        "quality_plus_counts": {} if args.skip_quality_plus else (pre_quality_plus_summary.get("counts", {}) if isinstance(pre_quality_plus_summary, dict) else {}),
        "coverage_counts": {} if args.skip_coverage else (pre_coverage_summary.get("counts", {}) if isinstance(pre_coverage_summary, dict) else {}),
        "interpretation_counts": {} if args.skip_interpretation else (pre_interpretation_summary.get("counts", {}) if isinstance(pre_interpretation_summary, dict) else {}),
        "assembly_counts": {} if args.skip_report_assembly else (pre_assembly_summary.get("counts", {}) if isinstance(pre_assembly_summary, dict) else {}),
        "evidence_sync_counts": {} if args.skip_contest_evidence_sync else (pre_evidence_sync_summary.get("counts", {}) if isinstance(pre_evidence_sync_summary, dict) else {}),
        "evidence_sync_status": None if args.skip_contest_evidence_sync else (pre_evidence_sync_summary.get("status") if isinstance(pre_evidence_sync_summary, dict) else None),
        "contest_qc_counts": {} if args.skip_contest_qc else (pre_contest_qc_summary.get("counts", {}) if isinstance(pre_contest_qc_summary, dict) else {}),
        "contest_qc_readiness": None if args.skip_contest_qc else (pre_contest_qc_summary.get("readiness") if isinstance(pre_contest_qc_summary, dict) else None),
        "repair_counts": {},
        "delivery_readiness": "pending",
        "finalize_counts": {
            "fail": sum(1 for c in pre_finalize_checks if c.get("status") == "fail"),
            "warn": sum(1 for c in pre_finalize_checks if c.get("status") == "warn"),
            "total": len(pre_finalize_checks),
        },
    }
    write_summary(project, pre_summary)

    if args.skip_competition_evidence:
        steps.append(skipped_step("competition_evidence", [py, str(EVIDENCE_SCRIPT), str(project)], "--skip-competition-evidence"))
    else:
        cmd = [py, str(EVIDENCE_SCRIPT), str(project)]
        if args.strict_competition_evidence:
            cmd.append("--strict")
        steps.append(run_command("competition_evidence", cmd, project, timeout=args.timeout))

    if args.skip_repair_advisor:
        steps.append(skipped_step("repair_advisor", [py, str(REPAIR_SCRIPT), str(project)], "--skip-repair-advisor"))
    else:
        cmd = [py, str(REPAIR_SCRIPT), str(project)]
        if args.strict_repair_advisor:
            cmd.append("--strict")
        steps.append(run_command("repair_advisor", cmd, project, timeout=args.timeout))

    if args.skip_competition_readiness:
        steps.append(skipped_step("competition_readiness", [py, str(COMPETITION_SCRIPT), str(project)], "--skip-competition-readiness"))
    else:
        cmd = [py, str(COMPETITION_SCRIPT), str(project)]
        if args.strict_competition_readiness:
            cmd.append("--strict")
        steps.append(run_command("competition_readiness", cmd, project, timeout=args.timeout))

    contest_qc_for_package = read_json(project / "06_过程记录" / "竞赛质控" / "contest_qc_gate.json")
    competition_for_package = read_json(project / "06_过程记录" / "竞赛就绪度" / "competition_readiness.json")
    blocking_reasons = [
        f"required step failed: {step.name}"
        for step in steps
        if not step.skipped and step.exit_code != 0
    ]
    if args.skeleton_only:
        blocking_reasons.append("--skeleton-only does not create a submission package")
    elif args.skip_finalize:
        blocking_reasons.append("--skip-finalize")
    if args.skip_contest_qc:
        blocking_reasons.append("final packaging requires contest QC")
    elif contest_qc_for_package.get("phase") != "final" or contest_qc_for_package.get("readiness") != "final_ready":
        blocking_reasons.append("contest QC is not final_ready")
    if args.skip_competition_readiness:
        blocking_reasons.append("final packaging requires competition readiness")
    elif competition_for_package.get("competition_ready") is not True:
        blocking_reasons.append("competition readiness is not competition_ready")

    finalize_cmd = [py, str(FINALIZE_SCRIPT), str(project), "--entry", args.entry]
    for report in args.report or []:
        finalize_cmd.extend(["--report", report])
    if args.strict:
        finalize_cmd.append("--strict")
    if args.zip:
        finalize_cmd.append("--zip")
    if args.include_raw_data:
        finalize_cmd.append("--include-raw-data")
    if args.no_code:
        finalize_cmd.append("--no-code")

    if blocking_reasons:
        steps.append(skipped_step("finalize", finalize_cmd, "; ".join(blocking_reasons)))
        steps.append(skipped_step("state_update_final", [py, str(STATE_SCRIPT), str(project), "--strict"], "finalize did not publish a current package"))
    else:
        finalize_result = run_command("finalize", finalize_cmd, project, timeout=args.timeout)
        steps.append(finalize_result)
        if finalize_result.exit_code == 0:
            steps.append(run_command("state_update_final", [py, str(STATE_SCRIPT), str(project), "--strict"], project, timeout=args.timeout))
        else:
            steps.append(skipped_step("state_update_final", [py, str(STATE_SCRIPT), str(project), "--strict"], "finalize failed"))

    skeleton_summary = read_json(project / "06_过程记录" / "model_skeleton" / "model_skeleton.json")
    domain_checker_templates = read_json(project / "06_过程记录" / "领域checker" / "domain_checker_templates.json")
    audit_summary = read_json(project / "06_过程记录" / "一致性检查" / "auto_report_audit.json")
    quality_plus_summary = read_json(project / "06_过程记录" / "质量门禁" / "quality_gate_plus.json")
    coverage_summary = read_json(project / "06_过程记录" / "问题覆盖" / "problem_coverage.json")
    interpretation_summary = read_json(project / "06_过程记录" / "结果解释" / "result_interpretation_draft.json")
    assembly_summary = read_json(project / "06_过程记录" / "报告拼装" / "report_section_assembly.json")
    evidence_sync_summary = read_json(project / "06_过程记录" / "竞赛质控" / "evidence_sync.json")
    contest_qc_summary = read_json(project / "06_过程记录" / "竞赛质控" / "contest_qc_gate.json")
    repair_summary = read_json(project / "06_过程记录" / "修复建议" / "repair_advice.json")
    competition_summary = read_json(project / "06_过程记录" / "竞赛就绪度" / "competition_readiness.json")
    finalize_step = next((step for step in steps if step.name == "finalize"), None)
    current_package_published = bool(
        finalize_step and not finalize_step.skipped and finalize_step.exit_code == 0
    )
    finalize_blocked = bool(
        not args.skeleton_only
        and not args.skip_finalize
        and finalize_step
        and finalize_step.skipped
    )
    manifest = (
        read_json(project / "07_提交包" / "submission_manifest.json")
        if current_package_published
        else {}
    )
    meta = read_json(project / "project_meta.json")

    fail_steps = [s for s in steps if not s.skipped and s.exit_code != 0]
    audit_counts = {} if args.skip_report_audit else (audit_summary.get("counts", {}) if isinstance(audit_summary, dict) else {})
    quality_plus_counts = {} if args.skip_quality_plus else (quality_plus_summary.get("counts", {}) if isinstance(quality_plus_summary, dict) else {})
    coverage_counts = {} if args.skip_coverage else (coverage_summary.get("counts", {}) if isinstance(coverage_summary, dict) else {})
    interpretation_counts = {} if args.skip_interpretation else (interpretation_summary.get("counts", {}) if isinstance(interpretation_summary, dict) else {})
    assembly_counts = {} if args.skip_report_assembly else (assembly_summary.get("counts", {}) if isinstance(assembly_summary, dict) else {})
    evidence_sync_counts = {} if args.skip_contest_evidence_sync else (evidence_sync_summary.get("counts", {}) if isinstance(evidence_sync_summary, dict) else {})
    contest_qc_counts = {} if args.skip_contest_qc else (contest_qc_summary.get("counts", {}) if isinstance(contest_qc_summary, dict) else {})
    repair_counts = {} if args.skip_repair_advisor else (repair_summary.get("counts", {}) if isinstance(repair_summary, dict) else {})
    competition_counts = {} if args.skip_competition_readiness else (competition_summary.get("counts", {}) if isinstance(competition_summary, dict) else {})
    finalize_checks = manifest.get("checks", []) if isinstance(manifest, dict) else []
    finalize_fail = sum(1 for c in finalize_checks if c.get("status") == "fail")
    finalize_warn = sum(1 for c in finalize_checks if c.get("status") == "warn")
    recommended_status, _, _ = status_from_steps(
        steps,
        meta.get("highest_contiguous_state"),
        args.skeleton_only,
        current_package_published=current_package_published,
        finalize_blocked=finalize_blocked,
    )

    summary = {
        "phase": "final",
        "generated_at": datetime.now().isoformat(timespec="seconds"),
        "project": str(project),
        "recommended_status": recommended_status,
        "highest_contiguous_state": meta.get("highest_contiguous_state"),
        "current_package_published": current_package_published,
        "final_package": str(project / "07_提交包") if current_package_published else "",
        "entry": args.entry,
        "strict": args.strict,
        "strict_numbers": args.strict_numbers,
        "steps": [asdict(s) for s in steps],
        "model_skeleton": {"primary_type": skeleton_summary.get("primary_type"), "primary_confidence": skeleton_summary.get("primary_confidence"), "route_count": len(skeleton_summary.get("routes", []))} if isinstance(skeleton_summary, dict) else {},
        "domain_checker_templates": {"checker_types": ",".join(domain_checker_templates.get("checker_types", [])), "checker_file_count": len(domain_checker_templates.get("checker_files", []))} if isinstance(domain_checker_templates, dict) else {},
        "audit_counts": audit_counts,
        "quality_plus_counts": quality_plus_counts,
        "coverage_counts": coverage_counts,
        "interpretation_counts": interpretation_counts,
        "assembly_counts": assembly_counts,
        "evidence_sync_counts": evidence_sync_counts,
        "evidence_sync_status": evidence_sync_summary.get("status") if isinstance(evidence_sync_summary, dict) else None,
        "contest_qc_counts": contest_qc_counts,
        "contest_qc_readiness": contest_qc_summary.get("readiness") if isinstance(contest_qc_summary, dict) else None,
        "repair_counts": repair_counts,
        "delivery_readiness": repair_summary.get("delivery_readiness") if isinstance(repair_summary, dict) else None,
        "competition_counts": competition_counts,
        "competition_readiness": competition_summary.get("readiness") if isinstance(competition_summary, dict) else None,
        "competition_ready": competition_summary.get("competition_ready") if isinstance(competition_summary, dict) else None,
        "finalize_counts": {"fail": finalize_fail, "warn": finalize_warn, "total": len(finalize_checks)},
    }
    json_path, md_path = write_summary(project, summary)

    print(f"Pipeline summary: {md_path}")
    print(f"Pipeline json: {json_path}")
    print(f"Recommended status: {recommended_status}")
    print(f"Highest contiguous state: {summary.get('highest_contiguous_state')}")
    if fail_steps or finalize_blocked:
        print("Failed steps:")
        for s in fail_steps:
            print(f"- {s.name}: exit_code={s.exit_code}")
        if finalize_blocked:
            reason = next(step.reason for step in steps if step.name == "finalize" and step.skipped)
            print(f"- finalize: blocked ({reason})")
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
