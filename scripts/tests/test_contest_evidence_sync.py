from __future__ import annotations

import csv
import sys
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parents[1]
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))

from contest_evidence_sync import build_sync, stable_id
from contest_qc_gate import QC_REL, REGISTRY_HEADERS, init_project


def write_rows(path: Path, rows: list[dict[str, str]]) -> None:
    with path.open("w", encoding="utf-8-sig", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=REGISTRY_HEADERS[path.name])
        writer.writeheader()
        writer.writerows(rows)


def make_discovery_project(project: Path, outside: Path) -> None:
    (project / "02_代码").mkdir(parents=True)
    (project / "02_代码" / "solve.py").write_text("print('solve')\n", encoding="utf-8")
    tables = project / "03_结果表格"
    tables.mkdir()
    (tables / "model_results.csv").write_text("metric,value\nobjective,1\n", encoding="utf-8")
    (tables / "sensitivity_results.xlsx").write_bytes(b"fixture-xlsx")
    (tables / "auto_report_audit.csv").write_text("status\npass\n", encoding="utf-8")
    outside.write_text("metric,value\nexternal,1\n", encoding="utf-8")
    (tables / "external.csv").symlink_to(outside)

    figures = project / "04_图表"
    figures.mkdir()
    (figures / "result.png").write_bytes(b"fixture-png")

    analysis = project / "06_过程记录" / "problem_analysis.md"
    analysis.parent.mkdir(parents=True)
    analysis.write_text(
        "# 题目解析\n\n## 任务清单\n\nQ1: 求满足容量约束的最小成本方案。\n\n"
        "## 数据清单\n\n附件包含成本和容量。\n",
        encoding="utf-8",
    )
    init_project(project)
    write_rows(project / QC_REL / "run_record.csv", [{
        "run_id": "R1",
        "problem_id": "fixture",
        "model_version": "v1",
        "command": "python 02_代码/solve.py",
        "entry_script": "02_代码/solve.py",
        "output_tables": "03_结果表格/model_results.csv",
        "output_figures": "04_图表/result.png",
        "run_status": "completed",
    }])


def test_stable_id_is_deterministic_and_identity_sensitive() -> None:
    first = stable_id("RSLT", "03_结果表格/model_results.csv")
    assert first == stable_id("RSLT", "03_结果表格/model_results.csv")
    assert first.startswith("RSLT-")
    assert first != stable_id("RSLT", "03_结果表格/other.csv")


def test_discovers_candidates_and_links_only_exact_completed_run_outputs(tmp_path: Path) -> None:
    project = tmp_path / "project"
    project.mkdir()
    make_discovery_project(project, tmp_path / "outside.csv")

    summary = build_sync(project)

    deliverables = summary.registries["deliverable_matrix.csv"].candidates
    assert [row["deliverable_id"] for row in deliverables] == ["D-Q1"]
    assert deliverables[0]["status"] == "candidate"

    results = summary.registries["result_registry.csv"].candidates
    assert {row["source_table"] for row in results} == {
        "03_结果表格/model_results.csv",
        "03_结果表格/sensitivity_results.xlsx",
    }
    linked = next(row for row in results if row["source_table"].endswith("model_results.csv"))
    assert linked["run_id"] == "R1"
    assert linked["source_script"] == "02_代码/solve.py"
    assert linked["validation_status"] == "candidate"
    unlinked = next(row for row in results if row["source_table"].endswith("sensitivity_results.xlsx"))
    assert unlinked["run_id"] == ""
    assert unlinked["source_script"] == ""

    figures = summary.registries["figure_evidence.csv"].candidates
    assert len(figures) == 1
    assert figures[0]["figure_path"] == "04_图表/result.png"
    assert figures[0]["run_id"] == "R1"
    assert figures[0]["validation_status"] == "candidate"
    assert summary.counts["ignored"] == 2
