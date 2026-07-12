#!/usr/bin/env python3
"""Contest-quality contract and evidence gate for modeling projects.

This is a deliberately small, executable integration of the high-value parts of
an expert contest-QC workflow: a current-question lock, deliverable tracking,
real-data PoCs, model/code handoff, mathematical checks, reproducible runs,
evidence-backed claims/figures, judge-risk findings, and final compliance.

It never certifies an award. It writes reviewable evidence under
``06_过程记录/竞赛质控`` and reports one of:
- ``blocked``: a required evidence chain is absent or contradicted;
- ``needs_review``: no hard block, but required review evidence is incomplete;
- ``early_ready`` / ``model_ready`` / ``final_ready``: the selected phase has
  the required machine-checkable evidence. Human modeling judgement still
  remains necessary.
"""
from __future__ import annotations

import argparse
import csv
import json
import sys
from dataclasses import asdict, dataclass
from datetime import datetime
from pathlib import Path
from typing import Any

QC_REL = Path("06_过程记录") / "竞赛质控"

REGISTRY_HEADERS: dict[str, list[str]] = {
    "deliverable_matrix.csv": [
        "deliverable_id", "problem_id", "subquestion", "required_output", "format",
        "evidence_needed", "owner", "status", "risk_note", "approval_source", "omission_reason", "accepted_by",
    ],
    "symbol_table.csv": ["symbol", "type", "meaning", "unit", "domain", "source", "status"],
    "assumption_log.csv": [
        "assumption_id", "statement", "affected_variables", "affected_constraints", "rationale",
        "validation_plan", "risk_if_false", "status",
    ],
    "poc_registry.csv": [
        "poc_id", "problem_id", "subquestion", "candidate_id", "model_version",
        "script_or_command", "source_data", "source_slice", "metric", "value", "unit",
        "runtime", "status", "failure_reason", "promoted_model_version", "notes",
    ],
    "math_verification.csv": [
        "check_id", "subquestion", "artifact", "location", "claim_id", "check_type",
        "input_ref", "expected_relation", "observed", "status", "severity", "minimum_fix", "owner",
    ],
    "run_record.csv": [
        "run_id", "problem_id", "model_version", "command", "entry_script", "input_files",
        "parameters", "seed", "solver", "solver_status", "warnings", "output_tables",
        "output_figures", "log_path", "started_at", "completed_at", "run_status", "superseded_by", "notes",
    ],
    "result_registry.csv": [
        "result_id", "deliverable_id", "problem_id", "scenario_id", "metric", "value", "unit",
        "comparison_or_baseline", "source_table", "source_figure", "source_script", "run_id",
        "validation_status", "frozen_at", "superseded_by", "notes",
    ],
    "claim_ledger.csv": [
        "claim_id", "location", "claim_text", "metric", "value", "unit", "scenario",
        "evidence_id", "evidence_type", "body_location", "status", "risk_note",
    ],
    "figure_evidence.csv": [
        "figure_id", "deliverable_id", "claim_id", "figure_path", "run_id", "caption", "post_figure_conclusion",
        "risk_note", "render_check_status", "human_visual_check", "visual_check_note", "validation_status",
    ],
    "consistency_audit.csv": [
        "audit_id", "claim_id", "artifact_a", "location_a", "artifact_b", "location_b",
        "mismatch_type", "expected", "observed", "severity", "minimum_fix", "owner", "status",
    ],
    "review_findings.csv": [
        "finding_id", "severity", "dimension", "score_risk", "artifact", "location",
        "issue", "impact", "minimum_fix", "owner", "status",
    ],
    "review_pass_items.csv": [
        "pass_item_id", "source_module", "claim_id", "file", "location", "value",
        "constraint_direction", "expected", "observed", "evidence_ref", "status", "notes",
    ],
}

MODEL_HANDOFF_TEMPLATE = """# 模型交接（model_handoff）

artifact_status: draft

## 当前锁定
- 题目/小问：待填写
- 对应交付物 ID：待填写
- 模型版本：v0

## 模型路线与选择理由
待填写：说明问题机制、主路线、baseline 及不选其他路线的原因。

## 变量、单位与定义
待填写：变量、参数、单位、定义域，并链接 `symbol_table.csv`。

## 目标与约束
待填写：目标函数、硬/软约束、边界条件和可行性判定。

## 输入与输出
待填写：真实数据路径、可信列、预处理/单位换算、结果表 schema、图表清单。

## PoC 与可复现运行
待填写：`poc_registry.csv` 的 passed 条目、正式 run_id、命令、seed/求解器设置。

## 验证与稳健性
待填写：量纲/边界/可行性检查、baseline、敏感性或风险分析、降级规则。

## 待解决缺口
待填写：任何不能由代码自行猜测的参数、单位、阈值、约束或输出格式。
"""

MODEL_REVIEW_TEMPLATE = """# 模型质量审查

artifact_status: draft

## 当前锁定
- 当前小问与交付物：待填写

## 路线质量
- 质量等级：blocked / usable-but-needs-review / national-first-candidate
- 任务契合：待填写
- baseline 与缺陷：待填写

## 数学对象
- 变量、单位、目标、约束、边界：待填写

## 结果与验证计划
- 结果表/图表：待填写
- PoC、检查、敏感性、复现：待填写

## 最小修复
待填写
"""

SUBMISSION_TEMPLATE = """# 提交与合规检查

artifact_status: draft
official_rule_source: unknown
rule_checked_at: unknown
anonymity_check: pending
reproducibility: pending
ai_disclosure_status: unknown

## 规则与格式
- 页数、命名、文件格式、附件要求：待核对官方规则。

## 匿名性
- 标题页、页眉页脚、PDF 元数据、文件名、代码注释、附录：待核对。

## 复现
- 核心运行命令、输入、环境、输出路径：待填写。

## AI 使用披露
- 仅在官方规则要求时填写最终披露位置；不要把披露文字塞入正文或图表。

## 未解决阻塞项
- 待填写。
"""

AI_LOG_TEMPLATE = """# AI 使用记录

仅当当前竞赛规则或用户要求追踪 AI 使用时填写。本记录是提交材料，不应自动写入论文正文、图表或代码注释。

- 官方规则来源与日期：待填写
- 工具/模型：待填写
- 使用阶段：待填写
- 采用内容：待填写
- 人工核验与修改：待填写
- 最终披露位置：待填写
"""


@dataclass
class Check:
    id: str
    level: str
    status: str  # pass / warn / fail
    message: str
    evidence: str = ""
    minimum_fix: str = ""


def rel(project: Path, path: Path) -> str:
    try:
        return str(path.relative_to(project))
    except ValueError:
        return str(path)


def read_text(path: Path) -> str:
    try:
        return path.read_text(encoding="utf-8", errors="ignore")
    except Exception:
        return ""


def load_csv(path: Path) -> list[dict[str, str]]:
    if not path.exists():
        return []
    try:
        with path.open("r", encoding="utf-8-sig", newline="") as f:
            return [dict(row) for row in csv.DictReader(f)]
    except Exception:
        return []


def write_csv_template(path: Path, headers: list[str], force: bool) -> None:
    if path.exists() and not force:
        return
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8-sig", newline="") as f:
        csv.DictWriter(f, fieldnames=headers).writeheader()


def write_text_template(path: Path, content: str, force: bool) -> None:
    if path.exists() and not force:
        return
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")


def init_project(project: Path, force: bool = False) -> list[Path]:
    qc = project / QC_REL
    qc.mkdir(parents=True, exist_ok=True)
    for name, headers in REGISTRY_HEADERS.items():
        write_csv_template(qc / name, headers, force)
    write_text_template(qc / "model_handoff.md", MODEL_HANDOFF_TEMPLATE, force)
    write_text_template(qc / "model_quality_review.md", MODEL_REVIEW_TEMPLATE, force)
    write_text_template(qc / "submission_checklist.md", SUBMISSION_TEMPLATE, force)
    write_text_template(qc / "ai_usage_log.md", AI_LOG_TEMPLATE, force)
    hub_state = qc / "hub_state.json"
    if force or not hub_state.exists():
        hub_state.write_text(json.dumps({
            "artifact_status": "draft",
            "current_subquestion": "unknown",
            "deliverables_missing": [],
            "open_blockers": [],
            "allowed_next_action": "填写 problem_analysis.md 与 deliverable_matrix.csv",
            "paper_ready_claims": [],
            "compliance_status": "unknown",
            "updated_at": datetime.now().isoformat(timespec="seconds"),
        }, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return sorted(p for p in qc.iterdir() if p.is_file())


def non_template(text: str, minimum: int = 100) -> bool:
    stripped = "".join(text.split())
    placeholders = ("待填写", "待补充", "TODO", "unknown")
    return len(stripped) >= minimum and not any(token in text for token in placeholders)


def clean(value: Any) -> str:
    return str(value or "").strip()


def is_resolved(value: str) -> bool:
    return clean(value).lower() in {"resolved", "fixed", "closed", "passed", "pass", "accepted"}


def path_exists_from_project(project: Path, value: str) -> bool:
    raw = clean(value)
    if not raw:
        return False
    root = project.resolve()
    candidate = Path(raw).expanduser()
    if not candidate.is_absolute():
        candidate = root / candidate
    try:
        resolved = candidate.resolve(strict=True)
        resolved.relative_to(root)
    except (OSError, RuntimeError, ValueError):
        return False
    return resolved.is_file()


def evaluate(project: Path, phase: str) -> dict[str, Any]:
    qc = project / QC_REL
    checks: list[Check] = []

    def add(check_id: str, level: str, status: str, message: str, evidence: str = "", minimum_fix: str = "") -> None:
        checks.append(Check(check_id, level, status, message, evidence, minimum_fix))

    problem = project / "06_过程记录" / "problem_analysis.md"
    problem_ok = problem.exists() and non_template(read_text(problem), minimum=120)
    add(
        "problem_lock", "early", "pass" if problem_ok else "fail",
        "题目解析已形成可用锁定" if problem_ok else "题目解析缺失、过短或仍是空模板",
        rel(project, problem), "补齐每问目标、数据、约束、输出和题型路由。",
    )

    matrix_path = qc / "deliverable_matrix.csv"
    deliverables = load_csv(matrix_path)
    statuses = [clean(row.get("status")).lower() for row in deliverables]
    valid_deliverables = [row for row in deliverables if clean(row.get("deliverable_id")) and clean(row.get("required_output"))]
    if not valid_deliverables:
        add("deliverable_matrix", "early", "fail", "没有已定义的题目交付物", rel(project, matrix_path), "每个小问/输出至少填写一行。")
    elif any(status == "blocked" for status in statuses):
        add("deliverable_matrix", "early", "fail", "存在 blocked 交付物", rel(project, matrix_path), "解除阻塞或记录经规则/用户批准的 omission。")
    else:
        unsupported_omissions = [
            row for row in valid_deliverables
            if clean(row.get("status")).lower() == "accepted_omission"
            and not all(clean(row.get(field)) for field in ("approval_source", "omission_reason", "accepted_by"))
        ]
        if unsupported_omissions:
            add("deliverable_matrix", "early", "fail", "accepted_omission 缺少批准来源、原因或批准人", rel(project, matrix_path), "补齐 approval_source、omission_reason 和 accepted_by。")
        elif phase == "early":
            add("deliverable_matrix", "early", "pass", f"已锁定 {len(valid_deliverables)} 个交付物", rel(project, matrix_path))
        else:
            unfinished = [s for s in statuses if s not in {"provided", "accepted_omission"}]
            add(
                "deliverable_matrix", "model", "pass" if not unfinished else "fail",
                "所有交付物已提供或有正式豁免" if not unfinished else f"仍有 {len(unfinished)} 个交付物未完成",
                rel(project, matrix_path), "将所有 required/in_progress 行推进为 provided，或附理由标记 accepted_omission。",
            )

    handoff_path = qc / "model_handoff.md"
    handoff = read_text(handoff_path)
    handoff_sections = ("## 当前锁定", "## 模型路线与选择理由", "## 变量、单位与定义", "## 目标与约束", "## 输入与输出", "## 验证与稳健性")
    handoff_ok = all(section in handoff for section in handoff_sections) and non_template(handoff, minimum=240)
    if phase == "early":
        add("model_handoff", "early", "pass" if handoff_path.exists() else "warn", "模型交接模板存在" if handoff_path.exists() else "缺少 model_handoff.md", rel(project, handoff_path))
    else:
        add(
            "model_handoff", "model", "pass" if handoff_ok else "fail",
            "模型交接包含变量、单位、约束、输入输出与验证计划" if handoff_ok else "模型交接仍是模板或缺少不可猜测的建模事实",
            rel(project, handoff_path), "补齐路线理由、变量/单位、目标/约束、真实输入、结果 schema 和验证计划。",
        )

    if phase in {"model", "final"}:
        poc_path = qc / "poc_registry.csv"
        pocs = load_csv(poc_path)
        passed_pocs = [r for r in pocs if clean(r.get("status")).lower() == "passed"]
        real_pocs = [
            r for r in passed_pocs
            if clean(r.get("source_data")) and clean(r.get("source_slice"))
            and "synthetic" not in clean(r.get("source_data")).lower()
            and "mock" not in clean(r.get("source_data")).lower()
            and path_exists_from_project(project, clean(r.get("source_data")))
        ]
        add(
            "real_data_poc", "model", "pass" if real_pocs else "fail",
            f"存在 {len(real_pocs)} 个可追溯真实数据 PoC" if real_pocs else "缺少通过的、可追溯到本项目真实附件的数据 PoC",
            rel(project, poc_path), "记录 passed PoC 的 source_data、source_slice、命令、指标和值。",
        )

        verification_path = qc / "math_verification.csv"
        verifications = load_csv(verification_path)
        open_verification = [r for r in verifications if clean(r.get("status")).lower() in {"fail", "blocked", ""}]
        passed_verification = [r for r in verifications if clean(r.get("status")).lower() in {"passed", "pass", "non_applicable"}]
        add(
            "math_verification", "model", "pass" if passed_verification and not open_verification else "fail",
            "数学/约束/单位检查已记录且无开放硬问题" if passed_verification and not open_verification else "缺少数学检查，或仍有 fail/blocked 检查项",
            rel(project, verification_path), "至少记录量纲、边界或约束等具体检查，并修复所有硬失败。",
        )

        runs_path = qc / "run_record.csv"
        runs = load_csv(runs_path)
        completed_run_rows = [
            r for r in runs
            if clean(r.get("run_status")).lower() == "completed"
            and clean(r.get("run_id"))
            and path_exists_from_project(project, clean(r.get("entry_script")))
        ]
        completed_runs = {clean(r.get("run_id")) for r in completed_run_rows}
        add(
            "reproducible_run", "model", "pass" if completed_runs else "fail",
            f"存在 {len(completed_runs)} 个完成且入口脚本可定位的可复现运行" if completed_runs else "缺少 run_status=completed 且 entry_script 可定位的正式运行记录",
            rel(project, runs_path), "记录命令、入口脚本、输入、参数、seed、输出和 run_id。",
        )

        result_path = qc / "result_registry.csv"
        results = load_csv(result_path)
        allowed_result_status = {"computed", "checked", "paper_ready"}
        valid_results = [
            r for r in results
            if clean(r.get("validation_status")).lower() in allowed_result_status
            and clean(r.get("run_id")) in completed_runs
            and path_exists_from_project(project, clean(r.get("source_table")))
            and path_exists_from_project(project, clean(r.get("source_script")))
        ]
        add(
            "result_registry", "model", "pass" if valid_results else "fail",
            f"存在 {len(valid_results)} 个可追溯结果" if valid_results else "结果登记表缺少指向 completed run、源表和源脚本的有效结果",
            rel(project, result_path), "每个关键结果填 result_id、单位、存在的 source_table/source_script、run_id、validation_status。",
        )

    if phase == "final":
        results = load_csv(qc / "result_registry.csv")
        ready_results = [
            r for r in results
            if clean(r.get("validation_status")).lower() == "paper_ready"
            and clean(r.get("run_id")) in completed_runs
            and path_exists_from_project(project, clean(r.get("source_table")))
            and path_exists_from_project(project, clean(r.get("source_script")))
        ]
        result_ids = {clean(r.get("result_id")) for r in ready_results}
        figures_path = qc / "figure_evidence.csv"
        figures = load_csv(figures_path)
        ready_figure_rows = [
            r for r in figures
            if clean(r.get("validation_status")).lower() == "paper_ready"
            and clean(r.get("run_id")) in completed_runs
            and clean(r.get("caption"))
            and clean(r.get("post_figure_conclusion"))
            and (clean(r.get("render_check_status")).lower() == "passed" or clean(r.get("human_visual_check")).lower() == "passed")
            and path_exists_from_project(project, clean(r.get("figure_path")))
        ]
        figure_ids = {clean(r.get("figure_id")) for r in ready_figure_rows}
        claims_path = qc / "claim_ledger.csv"
        claims = load_csv(claims_path)
        paper_claims = [r for r in claims if clean(r.get("status")).lower() == "paper_ready"]
        bad_claims = [r for r in paper_claims if clean(r.get("evidence_id")) not in result_ids | figure_ids]
        add(
            "paper_claim_evidence", "final", "pass" if paper_claims and not bad_claims else "fail",
            f"存在 {len(paper_claims)} 条可追溯 paper_ready 主张" if paper_claims and not bad_claims else "论文级主张缺少 paper_ready result/figure 证据映射",
            rel(project, claims_path), "每条摘要/结论主张要映射到 paper_ready 的 result_id 或 figure_id。",
        )
        provided_deliverable_ids = {
            clean(row.get("deliverable_id")) for row in valid_deliverables
            if clean(row.get("status")).lower() == "provided"
        }
        evidenced_deliverable_ids = {
            clean(row.get("deliverable_id")) for row in ready_results + ready_figure_rows
            if clean(row.get("deliverable_id"))
        }
        missing_deliverable_evidence = sorted(provided_deliverable_ids - evidenced_deliverable_ids)
        add(
            "deliverable_evidence_coverage", "final", "pass" if not missing_deliverable_evidence else "fail",
            "每个已提供交付物都有 paper_ready 结果或图表证据" if not missing_deliverable_evidence else f"缺少交付物证据映射：{', '.join(missing_deliverable_evidence)}",
            rel(project, qc / "deliverable_matrix.csv"), "为每个 provided deliverable 填 result_registry 或 figure_evidence 的 deliverable_id。",
        )
        add(
            "paper_figure_evidence", "final", "pass" if figure_ids else "warn",
            f"存在 {len(figure_ids)} 张经渲染或人工检查的 paper_ready 图" if figure_ids else "尚无 paper_ready 图表；若结论不依赖图表可说明原因，否则补图和可读性检查。",
            rel(project, figures_path), "为关键图表记录 run_id、caption、结论、视觉检查和 validation_status。",
        )

        review_path = qc / "review_findings.csv"
        findings = load_csv(review_path)
        open_high = [
            r for r in findings
            if clean(r.get("severity")).upper() in {"P0", "P1"} and not is_resolved(clean(r.get("status")))
        ]
        add(
            "judge_risk", "final", "pass" if not open_high else "fail",
            "不存在开放 P0/P1 评委风险" if not open_high else f"存在 {len(open_high)} 个未解决 P0/P1 风险",
            rel(project, review_path), "优先修复 P0/P1，再处理 presentation 类问题。",
        )

        consistency_path = qc / "consistency_audit.csv"
        consistency_rows = load_csv(consistency_path)
        open_consistency = [
            row for row in consistency_rows
            if (clean(row.get("severity")).upper() in {"P0", "P1"} and not is_resolved(clean(row.get("status"))))
            or clean(row.get("status")).lower() in {"fail", "blocked"}
        ]
        add(
            "consistency_audit", "final", "pass" if not open_consistency else "fail",
            "不存在开放的高风险一致性问题" if not open_consistency else f"存在 {len(open_consistency)} 个开放的一致性问题",
            rel(project, consistency_path), "修复值、单位、场景、baseline 或 validation_status 冲突，并记录 closed/resolved。",
        )

        pass_items_path = qc / "review_pass_items.csv"
        pass_items = [r for r in load_csv(pass_items_path) if clean(r.get("status")).lower() in {"passed", "pass"}]
        concrete_passes = [
            r for r in pass_items
            if all(clean(r.get(k)) for k in ("file", "location", "value", "constraint_direction", "observed"))
        ]
        add(
            "concrete_final_checks", "final", "pass" if len(concrete_passes) >= 5 else "warn",
            f"已记录 {len(concrete_passes)} 项具体通过检查" if len(concrete_passes) >= 5 else "最终审查不足 5 项可定位的通过证据",
            rel(project, pass_items_path), "记录文件、位置、值、预期关系、观测结果和证据来源。",
        )

        checklist_path = qc / "submission_checklist.md"
        checklist = read_text(checklist_path)
        compliance_ok = (
            "official_rule_source:" in checklist and "official_rule_source: unknown" not in checklist
            and "anonymity_check: passed" in checklist
            and "reproducibility: passed" in checklist
            and any(f"ai_disclosure_status: {value}" in checklist for value in ("passed", "not_required"))
        )
        add(
            "submission_compliance", "final", "pass" if compliance_ok else "fail",
            "官方规则、匿名、复现和 AI 披露状态均已明确" if compliance_ok else "提交合规清单仍缺官方规则、匿名、复现或 AI 披露状态",
            rel(project, checklist_path), "用当前官方规则来源填充 checklist，并完成匿名/复现/AI 披露核对。",
        )

    counts = {status: sum(c.status == status for c in checks) for status in ("pass", "warn", "fail")}
    if counts["fail"]:
        readiness = "blocked"
    elif counts["warn"]:
        readiness = "needs_review"
    else:
        readiness = {"early": "early_ready", "model": "model_ready", "final": "final_ready"}[phase]
    return {
        "schema_version": "1.0",
        "generated_at": datetime.now().isoformat(timespec="seconds"),
        "project": str(project),
        "phase": phase,
        "readiness": readiness,
        "counts": counts,
        "checks": [asdict(c) for c in checks],
        "quality_boundary": "final_ready is a documented contest-QC state, not an award guarantee.",
    }


def write_outputs(project: Path, summary: dict[str, Any]) -> tuple[Path, Path]:
    out_dir = project / QC_REL
    out_dir.mkdir(parents=True, exist_ok=True)
    json_path = out_dir / "contest_qc_gate.json"
    md_path = out_dir / "contest_qc_gate.md"
    json_path.write_text(json.dumps(summary, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    lines = ["# 竞赛质控门禁\n\n"]
    lines.append(f"- phase：`{summary['phase']}`\n")
    lines.append(f"- readiness：**{summary['readiness']}**\n")
    lines.append(f"- pass/warn/fail：{summary['counts']['pass']}/{summary['counts']['warn']}/{summary['counts']['fail']}\n")
    lines.append("- 口径：`final_ready` 只表示证据链与质控材料达到当前门禁要求，不保证获奖。\n\n")
    lines.append("| 层级 | 检查项 | 状态 | 说明 | 证据 | 最小修复 |\n|---|---|---|---|---|---|\n")
    icon = {"pass": "✅ pass", "warn": "⚠️ warn", "fail": "❌ fail"}
    for check in summary["checks"]:
        message = clean(check["message"]).replace("|", "/")
        evidence = clean(check["evidence"]).replace("|", "/")
        fix = clean(check["minimum_fix"]).replace("|", "/")
        lines.append(f"| {check['level']} | {check['id']} | {icon[check['status']]} | {message} | {evidence} | {fix} |\n")
    md_path.write_text("".join(lines), encoding="utf-8")
    return json_path, md_path


def main() -> int:
    parser = argparse.ArgumentParser(description="Initialize and run contest-quality evidence gates.")
    parser.add_argument("project", help="Modeling project directory")
    parser.add_argument("--init", action="store_true", help="Create non-destructive QC registries and templates")
    parser.add_argument("--force-templates", action="store_true", help="Overwrite only QC templates/headers; never delete project data")
    parser.add_argument("--phase", choices=("early", "model", "final"), default="final")
    parser.add_argument("--strict", action="store_true", help="Exit non-zero unless the selected phase is ready")
    args = parser.parse_args()
    project = Path(args.project).expanduser().resolve()
    if not project.exists():
        print(f"Project not found: {project}", file=sys.stderr)
        return 2
    if args.init:
        files = init_project(project, force=args.force_templates)
        print(f"QC templates: {len(files)} files under {project / QC_REL}")
    summary = evaluate(project, args.phase)
    json_path, md_path = write_outputs(project, summary)
    print(f"Contest QC ({args.phase}): {summary['readiness']}")
    print(f"Report: {md_path}")
    print(f"JSON: {json_path}")
    if args.strict and summary["readiness"] != f"{args.phase}_ready":
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
