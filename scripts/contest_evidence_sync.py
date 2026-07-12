#!/usr/bin/env python3
"""Discover review-only candidates for Contest QC evidence registries."""
from __future__ import annotations

import csv
import hashlib
import re
from dataclasses import dataclass, field
from pathlib import Path

from contest_qc_gate import QC_REL, REGISTRY_HEADERS
from problem_coverage_tracker import extract_questions, make_qid


TARGET_REGISTRIES = (
    "deliverable_matrix.csv",
    "result_registry.csv",
    "figure_evidence.csv",
)
CONTROL_TABLE_NAMES = {
    "auto_report_audit.csv",
    "data_audit.csv",
    "pipeline_run_summary.csv",
    "submission_manifest.csv",
}
TABLE_SUFFIXES = {".csv", ".xlsx"}
FIGURE_SUFFIXES = {".png", ".jpg", ".jpeg", ".pdf", ".svg"}


@dataclass
class RegistrySync:
    name: str
    candidates: list[dict[str, str]]
    merged_rows: list[dict[str, str]]
    added: int = 0
    updated: int = 0
    unchanged: int = 0
    conflicts: list[str] = field(default_factory=list)


@dataclass
class SyncSummary:
    project: Path
    registries: dict[str, RegistrySync]
    counts: dict[str, int]
    warnings: list[str]
    ignored: list[dict[str, str]]


def stable_id(prefix: str, identity: str) -> str:
    digest = hashlib.sha256(identity.encode("utf-8")).hexdigest()[:10].upper()
    return f"{prefix}-{digest}"


def safe_relative_file(project: Path, path: Path) -> str | None:
    try:
        resolved = path.resolve(strict=True)
        return resolved.relative_to(project.resolve()).as_posix()
    except (FileNotFoundError, OSError, RuntimeError, ValueError):
        return None


def load_rows(path: Path) -> list[dict[str, str]]:
    if not path.exists():
        return []
    with path.open("r", encoding="utf-8-sig", newline="") as handle:
        return [dict(row) for row in csv.DictReader(handle)]


def empty_row(name: str, **values: str) -> dict[str, str]:
    row = {field_name: "" for field_name in REGISTRY_HEADERS[name]}
    row.update(values)
    return row


def split_paths(value: str) -> list[str]:
    return [part.strip() for part in re.split(r"[;,\n]+", value or "") if part.strip()]


def completed_run_index(project: Path) -> tuple[dict[str, list[dict[str, str]]], dict[str, list[dict[str, str]]]]:
    runs = load_rows(project / QC_REL / "run_record.csv")
    table_index: dict[str, list[dict[str, str]]] = {}
    figure_index: dict[str, list[dict[str, str]]] = {}
    for run in runs:
        if (run.get("run_status") or "").strip().lower() != "completed":
            continue
        for value, index in ((run.get("output_tables", ""), table_index), (run.get("output_figures", ""), figure_index)):
            for raw_path in split_paths(value):
                relative = safe_relative_file(project, project / raw_path)
                if relative:
                    index.setdefault(relative, []).append(run)
    return table_index, figure_index


def linked_run(index: dict[str, list[dict[str, str]]], relative: str, warnings: list[str]) -> dict[str, str] | None:
    matches = index.get(relative, [])
    if len(matches) == 1:
        return matches[0]
    if len(matches) > 1:
        warnings.append(f"Ambiguous completed-run linkage: {relative}")
    return None


def build_sync(project: Path) -> SyncSummary:
    project = project.expanduser().resolve()
    warnings: list[str] = []
    ignored: list[dict[str, str]] = []
    table_runs, figure_runs = completed_run_index(project)

    problem_path = project / "06_过程记录" / "problem_analysis.md"
    problem_text = problem_path.read_text(encoding="utf-8", errors="ignore") if problem_path.exists() else ""
    deliverables: list[dict[str, str]] = []
    for index, question in enumerate(extract_questions(problem_text), start=1):
        qid = make_qid(index, question)
        deliverables.append(empty_row(
            "deliverable_matrix.csv",
            deliverable_id=f"D-{qid}",
            problem_id=project.name,
            subquestion=qid,
            required_output=question,
            status="candidate",
        ))

    results: list[dict[str, str]] = []
    table_dir = project / "03_结果表格"
    if table_dir.exists():
        for path in sorted(table_dir.rglob("*")):
            if not path.is_file() or path.suffix.lower() not in TABLE_SUFFIXES:
                continue
            relative = safe_relative_file(project, path)
            if relative is None:
                ignored.append({"path": str(path), "reason": "unsafe_or_external_path"})
                continue
            if path.name.lower() in CONTROL_TABLE_NAMES:
                ignored.append({"path": relative, "reason": "control_table"})
                continue
            run = linked_run(table_runs, relative, warnings)
            results.append(empty_row(
                "result_registry.csv",
                result_id=stable_id("RSLT", relative),
                problem_id=project.name,
                source_table=relative,
                source_script=(run.get("entry_script", "").strip() if run else ""),
                run_id=(run.get("run_id", "").strip() if run else ""),
                validation_status="candidate",
            ))

    figures: list[dict[str, str]] = []
    figure_dir = project / "04_图表"
    if figure_dir.exists():
        for path in sorted(figure_dir.rglob("*")):
            if not path.is_file() or path.suffix.lower() not in FIGURE_SUFFIXES:
                continue
            relative = safe_relative_file(project, path)
            if relative is None:
                ignored.append({"path": str(path), "reason": "unsafe_or_external_path"})
                continue
            run = linked_run(figure_runs, relative, warnings)
            figures.append(empty_row(
                "figure_evidence.csv",
                figure_id=stable_id("FIG", relative),
                figure_path=relative,
                run_id=(run.get("run_id", "").strip() if run else ""),
                validation_status="candidate",
            ))

    candidates = {
        "deliverable_matrix.csv": deliverables,
        "result_registry.csv": results,
        "figure_evidence.csv": figures,
    }
    registries = {
        name: RegistrySync(name, rows, load_rows(project / QC_REL / name))
        for name, rows in candidates.items()
    }
    return SyncSummary(
        project=project,
        registries=registries,
        counts={
            "discovered": sum(len(rows) for rows in candidates.values()),
            "ignored": len(ignored),
            "warnings": len(warnings),
        },
        warnings=warnings,
        ignored=ignored,
    )
