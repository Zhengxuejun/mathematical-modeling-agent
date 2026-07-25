from __future__ import annotations

import json
import sys
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parents[1]
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))

from competition_readiness_gate import as_bool, assess


def test_explicit_nonpass_status_never_falls_back_to_nonempty_metadata() -> None:
    assert not as_bool({"status": False, "paths": ["02_代码/model.py"], "model_keyword_hits": 9})
    assert not as_bool({"status": "checker_detected_no_machine_output", "paths": ["02_代码/check.py"]})
    assert not as_bool({"status": "template_checker_only", "issue_count": 0})
    assert as_bool({"status": "pass", "issue_count": 0})


def test_generated_checker_placeholders_do_not_poison_formal_model_readiness(tmp_path: Path) -> None:
    (tmp_path / "01_原始数据").mkdir()
    (tmp_path / "01_原始数据/input.csv").write_text("id,value\na,1\n", encoding="utf-8")
    (tmp_path / "02_代码/generated_checkers").mkdir(parents=True)
    (tmp_path / "02_代码/generated_checkers/check_optimization.py").write_text(
        "# TODO: generated checker starter\n",
        encoding="utf-8",
    )
    (tmp_path / "02_代码/solve_model.py").write_text(
        "# 决策变量 目标函数 约束 整数规划 优化\nprint('optimal')\n",
        encoding="utf-8",
    )
    (tmp_path / "03_结果表格").mkdir()
    (tmp_path / "03_结果表格/model_results.csv").write_text("metric,value\nobjective,1\n", encoding="utf-8")
    (tmp_path / "05_报告定稿").mkdir()
    (tmp_path / "05_报告定稿/report.md").write_text(
        "# Report\n决策变量、目标函数、约束、整数规划、敏感性和风险分析均已完成。\n",
        encoding="utf-8",
    )
    process = tmp_path / "06_过程记录"
    process.mkdir()
    (process / "problem_analysis.md").write_text("题目解析：" + "目标、数据、约束与输出。" * 20, encoding="utf-8")
    (process / "competition_evidence.json").write_text(
        json.dumps({"domain_checker": {"status": "pass", "issue_count": 0}}),
        encoding="utf-8",
    )

    summary = assess(tmp_path)
    placeholder = next(check for check in summary["checks"] if check["id"] == "placeholder_replaced")

    assert placeholder["status"] == "pass"


def test_failed_pipeline_summary_blocks_workflow_readiness(tmp_path: Path) -> None:
    (tmp_path / "01_原始数据").mkdir()
    (tmp_path / "01_原始数据/input.csv").write_text("id,value\na,1\n", encoding="utf-8")
    (tmp_path / "03_结果表格").mkdir()
    (tmp_path / "03_结果表格/model_results.csv").write_text(
        "metric,value\nobjective,1\n", encoding="utf-8"
    )
    (tmp_path / "05_报告定稿").mkdir()
    (tmp_path / "05_报告定稿/report.md").write_text("# Report\nCurrent results.\n", encoding="utf-8")
    process = tmp_path / "06_过程记录"
    process.mkdir()
    (process / "problem_analysis.md").write_text(
        "题目解析：" + "目标、数据、约束与输出。" * 20,
        encoding="utf-8",
    )
    pipeline_dir = process / "pipeline"
    pipeline_dir.mkdir()
    (pipeline_dir / "pipeline_run_summary.json").write_text(
        json.dumps({"phase": "pre_finalize", "recommended_status": "failed"}),
        encoding="utf-8",
    )

    summary = assess(tmp_path)
    pipeline_check = next(check for check in summary["checks"] if check["id"] == "pipeline_status")

    assert pipeline_check["status"] == "fail"
    assert summary["workflow_ready"] is False
    assert summary["competition_ready"] is False
