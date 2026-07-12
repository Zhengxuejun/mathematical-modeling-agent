from __future__ import annotations

import csv
import sys
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parents[1]
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))

from contest_qc_gate import (
    MODEL_HANDOFF_TEMPLATE,
    QC_REL,
    REGISTRY_HEADERS,
    evaluate,
    init_project,
    non_template,
    path_exists_from_project,
)


def write_rows(path: Path, rows: list[dict[str, str]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8-sig", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=REGISTRY_HEADERS[path.name])
        writer.writeheader()
        writer.writerows(rows)


def make_final_ready_fixture(project: Path) -> None:
    (project / "01_原始数据").mkdir(parents=True)
    (project / "01_原始数据" / "input.csv").write_text("id,value\na,1\n", encoding="utf-8")
    (project / "02_代码").mkdir()
    (project / "02_代码" / "solve.py").write_text("print('fixture solve')\n", encoding="utf-8")
    (project / "03_结果表格").mkdir()
    (project / "03_结果表格" / "result.csv").write_text("metric,value\nobjective,1\n", encoding="utf-8")
    analysis = project / "06_过程记录" / "problem_analysis.md"
    analysis.parent.mkdir(parents=True)
    analysis.write_text(
        "# 题目解析\n\n"
        "## 小问一\n在给定真实附件上确定满足容量约束的最小成本方案。\n\n"
        "## 数据清单\ninput.csv 包含实体 id 与价值 value，单位为万元。\n\n"
        "## 输出要求\n输出可行方案、总成本、约束残差和敏感性结论。\n\n"
        "## 题型路由\n这是一个有显式容量约束的离散优化问题，需与 baseline 比较。\n",
        encoding="utf-8",
    )
    init_project(project)
    qc = project / QC_REL
    (qc / "model_handoff.md").write_text(
        "# 模型交接\n\n"
        "## 当前锁定\n小问一；交付物 D1；模型版本 v1。\n\n"
        "## 模型路线与选择理由\n采用最小成本整数规划，并以贪心方案为 baseline。\n\n"
        "## 变量、单位与定义\nx_i 为是否选择实体，单位为 1；c_i 为成本，单位为万元。\n\n"
        "## 目标与约束\n最小化总成本，且容量、唯一性和非负约束必须满足。\n\n"
        "## 输入与输出\n输入为 01_原始数据/input.csv；输出为结果表与约束检查表。\n\n"
        "## PoC 与可复现运行\nPoC P1 在真实 input.csv 的首行上运行；正式运行 R1 固定 seed。\n\n"
        "## 验证与稳健性\n验证量纲、边界、容量残差，并比较 baseline。\n\n"
        "## 待解决缺口\n无。\n",
        encoding="utf-8",
    )
    write_rows(qc / "deliverable_matrix.csv", [{
        "deliverable_id": "D1", "problem_id": "fixture", "subquestion": "Q1",
        "required_output": "最小成本可行方案", "format": "csv", "evidence_needed": "R1",
        "owner": "model", "status": "provided", "risk_note": "",
    }])
    write_rows(qc / "poc_registry.csv", [{
        "poc_id": "P1", "problem_id": "fixture", "subquestion": "Q1", "candidate_id": "main",
        "model_version": "v1", "script_or_command": "python solve.py --slice 1",
        "source_data": "01_原始数据/input.csv", "source_slice": "row=1", "metric": "objective",
        "value": "1", "unit": "万元", "runtime": "0.01", "status": "passed",
        "failure_reason": "", "promoted_model_version": "v1", "notes": "",
    }])
    write_rows(qc / "math_verification.csv", [{
        "check_id": "V1", "subquestion": "Q1", "artifact": "model", "location": "constraint 1",
        "claim_id": "C1", "check_type": "constraint", "input_ref": "input.csv",
        "expected_relation": "residual <= 0", "observed": "0", "status": "passed",
        "severity": "P1", "minimum_fix": "", "owner": "model",
    }])
    write_rows(qc / "run_record.csv", [{
        "run_id": "R1", "problem_id": "fixture", "model_version": "v1", "command": "python solve.py",
        "entry_script": "02_代码/solve.py", "input_files": "01_原始数据/input.csv", "parameters": "capacity=1",
        "seed": "0", "solver": "scipy", "solver_status": "optimal", "warnings": "",
        "output_tables": "03_结果表格/result.csv", "output_figures": "04_图表/result.png", "log_path": "",
        "started_at": "2026-01-01", "completed_at": "2026-01-01", "run_status": "completed",
        "superseded_by": "", "notes": "",
    }])
    write_rows(qc / "result_registry.csv", [{
        "result_id": "RSLT1", "deliverable_id": "D1", "problem_id": "fixture", "scenario_id": "base", "metric": "objective",
        "value": "1", "unit": "万元", "comparison_or_baseline": "greedy", "source_table": "03_结果表格/result.csv",
        "source_figure": "", "source_script": "02_代码/solve.py", "run_id": "R1",
        "validation_status": "paper_ready", "frozen_at": "2026-01-01", "superseded_by": "", "notes": "",
    }])
    figure = project / "04_图表" / "result.png"
    figure.parent.mkdir(parents=True)
    figure.write_bytes(b"fixture")
    write_rows(qc / "figure_evidence.csv", [{
        "figure_id": "F1", "deliverable_id": "D1", "claim_id": "C1", "figure_path": "04_图表/result.png", "run_id": "R1",
        "caption": "结果", "post_figure_conclusion": "目标值为 1", "risk_note": "",
        "render_check_status": "passed", "human_visual_check": "", "visual_check_note": "fixture",
        "validation_status": "paper_ready",
    }])
    write_rows(qc / "claim_ledger.csv", [{
        "claim_id": "C1", "location": "conclusion", "claim_text": "目标值为 1", "metric": "objective",
        "value": "1", "unit": "万元", "scenario": "base", "evidence_id": "RSLT1",
        "evidence_type": "result", "body_location": "5.1", "status": "paper_ready", "risk_note": "",
    }])
    write_rows(qc / "review_findings.csv", [])
    write_rows(qc / "review_pass_items.csv", [{
        "pass_item_id": f"P{i}", "source_module": "review", "claim_id": "C1", "file": "report.md",
        "location": f"line {i}", "value": "1", "constraint_direction": "<=", "expected": "1",
        "observed": "1", "evidence_ref": "RSLT1", "status": "passed", "notes": "",
    } for i in range(1, 6)])
    (qc / "submission_checklist.md").write_text(
        "official_rule_source: https://example.org/rules\n"
        "rule_checked_at: 2026-01-01\n"
        "anonymity_check: passed\n"
        "reproducibility: passed\n"
        "ai_disclosure_status: not_required\n",
        encoding="utf-8",
    )


def test_init_creates_qc_registry_headers_and_early_gate_blocks_empty_project(tmp_path: Path) -> None:
    project = tmp_path / "project"
    project.mkdir()
    init_project(project)
    qc = project / QC_REL
    assert (qc / "deliverable_matrix.csv").exists()
    assert (qc / "model_handoff.md").exists()
    summary = evaluate(project, "early")
    assert summary["readiness"] == "blocked"
    assert any(check["id"] == "deliverable_matrix" and check["status"] == "fail" for check in summary["checks"])


def test_untouched_model_handoff_template_is_not_substantive() -> None:
    assert not non_template(MODEL_HANDOFF_TEMPLATE, minimum=240)


def test_evidence_path_must_resolve_inside_project(tmp_path: Path) -> None:
    project = tmp_path / "project"
    project.mkdir()
    inside = project / "input.csv"
    inside.write_text("id,value\na,1\n", encoding="utf-8")
    outside = tmp_path / "outside.csv"
    outside.write_text("id,value\nb,2\n", encoding="utf-8")
    escaping_link = project / "external.csv"
    escaping_link.symlink_to(outside)

    assert path_exists_from_project(project, "input.csv")
    assert not path_exists_from_project(project, str(outside))
    assert not path_exists_from_project(project, "../outside.csv")
    assert not path_exists_from_project(project, "external.csv")


def test_final_gate_requires_evidence_and_blocks_open_p1(tmp_path: Path) -> None:
    project = tmp_path / "project"
    project.mkdir()
    make_final_ready_fixture(project)
    early = evaluate(project, "early")
    assert early["readiness"] == "early_ready"
    summary = evaluate(project, "final")
    assert summary["readiness"] == "final_ready"

    (project / "02_代码" / "solve.py").unlink()
    broken_reference = evaluate(project, "model")
    assert broken_reference["readiness"] == "blocked"
    assert any(check["id"] == "reproducible_run" and check["status"] == "fail" for check in broken_reference["checks"])
    (project / "02_代码" / "solve.py").write_text("print('fixture solve')\n", encoding="utf-8")

    qc = project / QC_REL
    write_rows(qc / "review_findings.csv", [{
        "finding_id": "F1", "severity": "P1", "dimension": "evidence", "score_risk": "major",
        "artifact": "claim_ledger.csv", "location": "C1", "issue": "missing check", "impact": "claim blocked",
        "minimum_fix": "add verification", "owner": "model", "status": "open",
    }])
    blocked = evaluate(project, "final")
    assert blocked["readiness"] == "blocked"
    assert any(check["id"] == "judge_risk" and check["status"] == "fail" for check in blocked["checks"])
