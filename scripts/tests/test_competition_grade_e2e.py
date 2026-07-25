from __future__ import annotations

import csv
import json
import subprocess
import sys
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parents[1]
TEST_DIR = Path(__file__).resolve().parent
for directory in (SCRIPT_DIR, TEST_DIR):
    if str(directory) not in sys.path:
        sys.path.insert(0, str(directory))

from finalize_modeling_project import DEFAULT_DIRS
from submission_package_contract import validate_submission_package
from test_contest_qc_gate import make_final_ready_fixture, write_rows
from update_project_state import infer_states


def make_competition_project(tmp_path: Path) -> Path:
    project = tmp_path / "competition-project"
    project.mkdir()
    make_final_ready_fixture(project)
    for directory in DEFAULT_DIRS:
        (project / directory).mkdir(parents=True, exist_ok=True)

    (project / "00_题目与资料/problem.md").write_text(
        "# Problem\nDetermine the minimum-cost feasible plan and analyze robustness.\n",
        encoding="utf-8",
    )
    tables = {
        "data_audit.csv": "field,missing_rate,min,max\nvalue,0,1,1\n",
        "baseline_results.csv": "metric,value\nobjective,1.2\n",
        "model_results.csv": "metric,value\nobjective,1.0\n",
        "sensitivity_results.csv": "factor,objective\n0.9,1.1\n1.1,1.05\n",
        "robust_scenarios.csv": "scenario,objective\nbase,1.0\nstress,1.2\n",
    }
    for name, content in tables.items():
        (project / "03_结果表格" / name).write_text(content, encoding="utf-8")
    for name in ("result.png", "comparison.png", "sensitivity.png"):
        (project / "04_图表" / name).write_bytes(b"competition-figure-payload")

    report = """# Minimum-Cost Planning Report

## Summary

For Question 1, an integer-programming model reduces the baseline objective from 1.2 to 1.0 while satisfying every capacity constraint.

## 问题一

The decision variable selects each entity. The objective function minimizes total cost subject to capacity, uniqueness, and non-negativity constraints. The solver reports an optimal feasible solution with objective 1.0.

## Validation and risk

Constraint residuals are zero. Baseline comparison, sensitivity analysis, and robust stress scenarios show objectives between 1.0 and 1.2. The uncertainty range limits the claim to the supplied data.

## Conclusion

The minimum-cost feasible plan has objective 1.0; stress testing preserves feasibility.
"""
    (project / "05_报告定稿/report_draft.md").write_text(report, encoding="utf-8")
    consistency_dir = project / "06_过程记录/一致性检查"
    consistency_dir.mkdir(parents=True, exist_ok=True)
    (consistency_dir / "report_consistency_check.md").write_text(
        "# Consistency check\nAll claims, values, units, figures, and tables were checked.\n",
        encoding="utf-8",
    )
    (project / "02_代码/check_constraints.py").write_text(
        "def check_capacity(residuals):\n    return all(value <= 0 for value in residuals)\n",
        encoding="utf-8",
    )
    checker_dir = project / "06_过程记录/领域checker"
    checker_dir.mkdir(parents=True, exist_ok=True)
    (checker_dir / "domain_checker_final.json").write_text(
        json.dumps({
            "checker_type": "domain_checker",
            "issue_count": 0,
            "warn_count": 0,
            "checks": [{"id": "capacity", "status": "pass"}],
        }),
        encoding="utf-8",
    )
    return project


def test_full_competition_pipeline_publishes_latest_verified_report(tmp_path: Path) -> None:
    project = make_competition_project(tmp_path)
    report = project / "05_报告定稿/report_draft.md"
    expected_report = report.read_bytes()
    command = [
        sys.executable,
        str(SCRIPT_DIR / "modeling_pipeline.py"),
        str(project),
        "--entry",
        "02_代码/solve.py",
        "--report",
        "05_报告定稿/report_draft.md",
    ]

    result = subprocess.run(command, text=True, capture_output=True, timeout=60)

    assert result.returncode == 0, result.stdout + "\n" + result.stderr
    package = project / "07_提交包"
    validation = validate_submission_package(package)
    assert validation.valid, validation.reasons
    assert infer_states(project)[8].complete
    assert (package / "report_draft.md").read_bytes() == expected_report
    summary = json.loads((project / "06_过程记录/pipeline/pipeline_run_summary.json").read_text(encoding="utf-8"))
    assert summary["recommended_status"] == "completed"
    assert summary["current_package_published"] is True
    assert summary["contest_qc_readiness"] == "final_ready"
    assert summary["competition_ready"] is True
    assert summary["evidence_sync_status"] == "candidates_synced"
    assert summary["evidence_sync_counts"]["added"] > 0
    qc = project / "06_过程记录/竞赛质控"
    with (qc / "result_registry.csv").open("r", encoding="utf-8-sig", newline="") as handle:
        rows = list(csv.DictReader(handle))
    trusted = next(row for row in rows if row["source_table"] == "03_结果表格/result.csv")
    candidate = next(row for row in rows if row["source_table"] == "03_结果表格/model_results.csv")
    assert trusted["validation_status"] == "paper_ready"
    assert candidate["validation_status"] == "candidate"


def test_open_p1_risk_blocks_finalizer_and_new_manifest(tmp_path: Path) -> None:
    project = make_competition_project(tmp_path)
    write_rows(project / "06_过程记录/竞赛质控/review_findings.csv", [{
        "finding_id": "F1",
        "severity": "P1",
        "dimension": "evidence",
        "score_risk": "major",
        "artifact": "claim_ledger.csv",
        "location": "C1",
        "issue": "claim lacks independent verification",
        "impact": "submission claim is unsafe",
        "minimum_fix": "add verification",
        "owner": "model",
        "status": "open",
    }])
    command = [
        sys.executable,
        str(SCRIPT_DIR / "modeling_pipeline.py"),
        str(project),
        "--entry",
        "02_代码/solve.py",
        "--report",
        "05_报告定稿/report_draft.md",
    ]

    result = subprocess.run(command, text=True, capture_output=True, timeout=60)

    assert result.returncode == 1
    assert not (project / "07_提交包/submission_manifest.json").exists()
    summary = json.loads((project / "06_过程记录/pipeline/pipeline_run_summary.json").read_text(encoding="utf-8"))
    assert summary["contest_qc_readiness"] == "blocked"
    finalize = next(step for step in summary["steps"] if step["name"] == "finalize")
    assert finalize["skipped"]
    assert "contest QC is not final_ready" in finalize["reason"]


def test_previous_s8_does_not_make_blocked_rerun_completed(tmp_path: Path) -> None:
    project = make_competition_project(tmp_path)
    command = [
        sys.executable,
        str(SCRIPT_DIR / "modeling_pipeline.py"),
        str(project),
        "--entry",
        "02_代码/solve.py",
        "--report",
        "05_报告定稿/report_draft.md",
    ]

    first = subprocess.run(command, text=True, capture_output=True, timeout=60)
    assert first.returncode == 0, first.stdout + "\n" + first.stderr
    old_manifest = (project / "07_提交包/submission_manifest.json").read_bytes()

    write_rows(project / "06_过程记录/竞赛质控/review_findings.csv", [{
        "finding_id": "F1",
        "severity": "P1",
        "dimension": "evidence",
        "score_risk": "major",
        "artifact": "claim_ledger.csv",
        "location": "C1",
        "issue": "claim lacks independent verification",
        "impact": "submission claim is unsafe",
        "minimum_fix": "add verification",
        "owner": "model",
        "status": "open",
    }])

    second = subprocess.run(command, text=True, capture_output=True, timeout=60)

    assert second.returncode == 1
    assert (project / "07_提交包/submission_manifest.json").read_bytes() == old_manifest
    summary = json.loads((project / "06_过程记录/pipeline/pipeline_run_summary.json").read_text(encoding="utf-8"))
    assert summary["recommended_status"] == "blocked"
    assert summary["current_package_published"] is False
    assert summary["final_package"] == ""
    assert summary["finalize_counts"] == {"fail": 0, "warn": 0, "total": 0}
    finalize = next(step for step in summary["steps"] if step["name"] == "finalize")
    assert finalize["skipped"]
    assert "contest QC is not final_ready" in finalize["reason"]


def test_evidence_sync_failure_skips_contest_qc_and_finalizer(tmp_path: Path) -> None:
    project = make_competition_project(tmp_path)
    qc = project / "06_过程记录/竞赛质控"
    (qc / "result_registry.csv").write_text("wrong,header\na,b\n", encoding="utf-8")
    command = [
        sys.executable,
        str(SCRIPT_DIR / "modeling_pipeline.py"),
        str(project),
        "--entry",
        "02_代码/solve.py",
        "--report",
        "05_报告定稿/report_draft.md",
    ]

    result = subprocess.run(command, text=True, capture_output=True, timeout=60)

    assert result.returncode == 1
    summary = json.loads((project / "06_过程记录/pipeline/pipeline_run_summary.json").read_text(encoding="utf-8"))
    sync = next(step for step in summary["steps"] if step["name"] == "contest_evidence_sync")
    contest_qc = next(step for step in summary["steps"] if step["name"] == "contest_qc")
    finalize = next(step for step in summary["steps"] if step["name"] == "finalize")
    assert sync["exit_code"] == 2
    assert contest_qc["skipped"]
    assert contest_qc["reason"] == "contest evidence synchronization failed"
    assert finalize["skipped"]
