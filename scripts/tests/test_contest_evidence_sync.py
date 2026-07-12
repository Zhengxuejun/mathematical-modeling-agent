from __future__ import annotations

import csv
import json
import os
import subprocess
import sys
from pathlib import Path

import pytest

SCRIPT_DIR = Path(__file__).resolve().parents[1]
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))

from contest_evidence_sync import (
    RegistrySchemaError,
    build_sync,
    recover_transaction,
    stable_id,
    synchronize,
    write_transaction,
)
from contest_qc_gate import QC_REL, REGISTRY_HEADERS, init_project


def write_rows(path: Path, rows: list[dict[str, str]]) -> None:
    with path.open("w", encoding="utf-8-sig", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=REGISTRY_HEADERS[path.name])
        writer.writeheader()
        writer.writerows(rows)


def read_rows(path: Path) -> list[dict[str, str]]:
    with path.open("r", encoding="utf-8-sig", newline="") as handle:
        return [dict(row) for row in csv.DictReader(handle)]


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


def test_sync_is_idempotent_and_preserves_confirmed_rows(tmp_path: Path) -> None:
    project = tmp_path / "project"
    project.mkdir()
    make_discovery_project(project, tmp_path / "outside.csv")
    qc = project / QC_REL
    write_rows(qc / "deliverable_matrix.csv", [{
        "deliverable_id": "D-HUMAN",
        "problem_id": "fixture",
        "subquestion": "Q1",
        "required_output": "人工确认的最小成本方案",
        "status": "provided",
    }])
    write_rows(qc / "result_registry.csv", [{
        "result_id": "R-HUMAN",
        "deliverable_id": "D-HUMAN",
        "problem_id": "fixture",
        "source_table": "03_结果表格/model_results.csv",
        "source_script": "02_代码/solve.py",
        "run_id": "R1",
        "validation_status": "paper_ready",
    }])
    write_rows(qc / "figure_evidence.csv", [{
        "figure_id": "F-HUMAN",
        "deliverable_id": "D-HUMAN",
        "figure_path": "04_图表/result.png",
        "run_id": "R1",
        "caption": "人工图题",
        "validation_status": "paper_ready",
    }])

    first = synchronize(project)
    snapshots = {name: (qc / name).read_bytes() for name in (
        "deliverable_matrix.csv", "result_registry.csv", "figure_evidence.csv"
    )}
    second = synchronize(project)

    assert first.counts["added"] == 1
    assert second.counts["added"] == 0
    assert second.counts["updated"] == 0
    assert second.counts["unchanged"] == 4
    assert {name: (qc / name).read_bytes() for name in snapshots} == snapshots
    assert read_rows(qc / "deliverable_matrix.csv")[0]["status"] == "provided"
    result = next(row for row in read_rows(qc / "result_registry.csv") if row["source_table"].endswith("model_results.csv"))
    assert result["result_id"] == "R-HUMAN"
    assert result["validation_status"] == "paper_ready"
    figure = read_rows(qc / "figure_evidence.csv")[0]
    assert figure["caption"] == "人工图题"
    assert figure["validation_status"] == "paper_ready"


def test_dry_run_does_not_initialize_or_write_project(tmp_path: Path) -> None:
    project = tmp_path / "project"
    project.mkdir()
    (project / "03_结果表格").mkdir()
    (project / "03_结果表格" / "result.csv").write_text("metric,value\na,1\n", encoding="utf-8")

    summary = synchronize(project, dry_run=True)

    assert summary.counts["added"] == 1
    assert not (project / QC_REL).exists()


def test_malformed_registry_header_blocks_all_changes(tmp_path: Path) -> None:
    project = tmp_path / "project"
    project.mkdir()
    make_discovery_project(project, tmp_path / "outside.csv")
    qc = project / QC_REL
    malformed = qc / "result_registry.csv"
    malformed.write_text("wrong,header\na,b\n", encoding="utf-8")
    before = {name: (qc / name).read_bytes() for name in (
        "deliverable_matrix.csv", "result_registry.csv", "figure_evidence.csv"
    )}

    with pytest.raises(RegistrySchemaError):
        synchronize(project)

    assert {name: (qc / name).read_bytes() for name in before} == before
    assert not (qc / "evidence_sync.json").exists()


def test_dry_run_validates_existing_registry_headers_without_mutation(tmp_path: Path) -> None:
    project = tmp_path / "project"
    project.mkdir()
    make_discovery_project(project, tmp_path / "outside.csv")
    malformed = project / QC_REL / "figure_evidence.csv"
    malformed.write_text("wrong,header\na,b\n", encoding="utf-8")
    before = malformed.read_bytes()

    with pytest.raises(RegistrySchemaError):
        synchronize(project, dry_run=True)

    assert malformed.read_bytes() == before


def test_interrupted_transaction_is_recovered_from_journal(tmp_path: Path) -> None:
    qc = tmp_path / QC_REL
    qc.mkdir(parents=True)
    target = qc / "deliverable_matrix.csv"
    backup = qc / ".deliverable_matrix.csv.backup"
    temporary = qc / ".deliverable_matrix.csv.temporary"
    target.write_text("corrupted\n", encoding="utf-8")
    backup.write_text("original\n", encoding="utf-8")
    temporary.write_text("new\n", encoding="utf-8")
    journal = qc / ".evidence_sync.transaction.json"
    journal.write_text(json.dumps({
        "phase": "applying",
        "entries": [{
            "target": target.name,
            "backup": backup.name,
            "temporary": temporary.name,
            "had_original": True,
        }],
    }), encoding="utf-8")

    recover_transaction(qc)

    assert target.read_text(encoding="utf-8") == "original\n"
    assert not backup.exists()
    assert not temporary.exists()
    assert not journal.exists()


def test_corrupt_transaction_journal_is_preserved_for_manual_recovery(tmp_path: Path) -> None:
    qc = tmp_path / QC_REL
    qc.mkdir(parents=True)
    journal = qc / ".evidence_sync.transaction.json"
    journal.write_text("{truncated", encoding="utf-8")

    with pytest.raises(json.JSONDecodeError):
        recover_transaction(qc)

    assert journal.exists()
    assert journal.read_text(encoding="utf-8") == "{truncated"


def test_replacement_failure_rolls_back_every_target(tmp_path: Path) -> None:
    project = tmp_path / "project"
    project.mkdir()
    make_discovery_project(project, tmp_path / "outside.csv")
    summary = build_sync(project)
    qc = project / QC_REL
    before = {name: (qc / name).read_bytes() for name in summary.registries}
    calls = 0

    def fail_second_replace(source: str | os.PathLike[str], target: str | os.PathLike[str]) -> None:
        nonlocal calls
        calls += 1
        if calls == 2:
            raise OSError("injected replacement failure")
        os.replace(source, target)

    with pytest.raises(OSError, match="injected replacement failure"):
        write_transaction(project, summary.registries, {}, replace=fail_second_replace)

    assert {name: (qc / name).read_bytes() for name in before} == before
    assert not (qc / ".evidence_sync.transaction.json").exists()


def test_exact_run_linkage_conflict_is_reported_without_overwriting_manual_value(tmp_path: Path) -> None:
    project = tmp_path / "project"
    project.mkdir()
    make_discovery_project(project, tmp_path / "outside.csv")
    qc = project / QC_REL
    write_rows(qc / "result_registry.csv", [{
        "result_id": "R-HUMAN",
        "source_table": "03_结果表格/model_results.csv",
        "source_script": "02_代码/other.py",
        "run_id": "R-OLD",
        "validation_status": "checked",
    }])

    summary = synchronize(project)

    assert summary.counts["conflicts"] == 2
    row = read_rows(qc / "result_registry.csv")[0]
    assert row["source_script"] == "02_代码/other.py"
    assert row["run_id"] == "R-OLD"


def test_cli_writes_review_only_reports_and_returns_zero(tmp_path: Path) -> None:
    project = tmp_path / "project"
    project.mkdir()
    make_discovery_project(project, tmp_path / "outside.csv")

    result = subprocess.run(
        [sys.executable, str(SCRIPT_DIR / "contest_evidence_sync.py"), str(project)],
        text=True,
        capture_output=True,
        timeout=20,
    )

    assert result.returncode == 0, result.stdout + result.stderr
    assert "Candidates synced" in result.stdout
    payload = json.loads((project / QC_REL / "evidence_sync.json").read_text(encoding="utf-8"))
    assert payload["status"] == "candidates_synced"
    report = (project / QC_REL / "evidence_sync.md").read_text(encoding="utf-8")
    assert "待审核候选" in report
    assert "代表模型、结果或图表已经验证" in report


def test_cli_returns_one_for_duplicate_registry_identity(tmp_path: Path) -> None:
    project = tmp_path / "project"
    project.mkdir()
    make_discovery_project(project, tmp_path / "outside.csv")
    qc = project / QC_REL
    duplicate = {
        "problem_id": "fixture",
        "source_table": "03_结果表格/model_results.csv",
        "source_script": "02_代码/solve.py",
        "run_id": "R1",
        "validation_status": "checked",
    }
    write_rows(qc / "result_registry.csv", [
        {**duplicate, "result_id": "R1"},
        {**duplicate, "result_id": "R2"},
    ])

    result = subprocess.run(
        [sys.executable, str(SCRIPT_DIR / "contest_evidence_sync.py"), str(project)],
        text=True,
        capture_output=True,
        timeout=20,
    )

    assert result.returncode == 1
    assert "conflicts=1" in result.stdout


def test_cli_returns_two_for_schema_error(tmp_path: Path) -> None:
    project = tmp_path / "project"
    project.mkdir()
    make_discovery_project(project, tmp_path / "outside.csv")
    (project / QC_REL / "result_registry.csv").write_text("wrong,header\na,b\n", encoding="utf-8")

    result = subprocess.run(
        [sys.executable, str(SCRIPT_DIR / "contest_evidence_sync.py"), str(project)],
        text=True,
        capture_output=True,
        timeout=20,
    )

    assert result.returncode == 2
    assert "Registry header mismatch" in result.stderr
