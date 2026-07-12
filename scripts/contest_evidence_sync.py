#!/usr/bin/env python3
"""Discover review-only candidates for Contest QC evidence registries."""
from __future__ import annotations

import argparse
import csv
import fcntl
import hashlib
import io
import json
import os
import re
import shutil
import sys
import uuid
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Callable

from contest_qc_gate import QC_REL, REGISTRY_HEADERS, init_project
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
IDENTITY_FIELDS = {
    "deliverable_matrix.csv": "subquestion",
    "result_registry.csv": "source_table",
    "figure_evidence.csv": "figure_path",
}
TRANSACTION_NAME = ".evidence_sync.transaction.json"
LOCK_NAME = ".evidence_sync.lock"


class RegistrySchemaError(ValueError):
    """Raised when an existing Contest QC registry has an unsafe schema."""


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


def normalize_question_id(value: str) -> str:
    translations = {"一": "1", "二": "2", "三": "3", "四": "4", "五": "5", "六": "6", "七": "7", "八": "8", "九": "9", "十": "10"}
    cleaned = re.sub(r"\s+", "", value or "").upper()
    match = re.fullmatch(r"Q?([一二三四五六七八九十]|\d+)", cleaned)
    if not match:
        return cleaned
    number = translations.get(match.group(1), match.group(1))
    return f"Q{number}"


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
        qid = normalize_question_id(make_qid(index, question))
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


def validate_header(path: Path, expected: list[str]) -> None:
    if not path.exists():
        return
    with path.open("r", encoding="utf-8-sig", newline="") as handle:
        actual = next(csv.reader(handle), [])
    if actual != expected:
        raise RegistrySchemaError(
            f"Registry header mismatch for {path}: expected {expected}, got {actual}"
        )


def registry_identity(name: str, row: dict[str, str]) -> str:
    value = (row.get(IDENTITY_FIELDS[name]) or "").strip()
    if name == "deliverable_matrix.csv":
        return normalize_question_id(value)
    return value.replace("\\", "/")


def merge_registry(
    name: str,
    existing: list[dict[str, str]],
    candidates: list[dict[str, str]],
) -> RegistrySync:
    rows = [{field_name: row.get(field_name, "") for field_name in REGISTRY_HEADERS[name]} for row in existing]
    by_identity: dict[str, int] = {}
    conflicts: list[str] = []
    for index, row in enumerate(rows):
        identity = registry_identity(name, row)
        if not identity:
            continue
        if identity in by_identity:
            conflicts.append(f"Duplicate existing identity in {name}: {identity}")
        else:
            by_identity[identity] = index

    added = 0
    updated = 0
    unchanged = 0
    for candidate in candidates:
        identity = registry_identity(name, candidate)
        if identity not in by_identity:
            rows.append(dict(candidate))
            by_identity[identity] = len(rows) - 1
            added += 1
            continue
        row = rows[by_identity[identity]]
        changed = False
        for field_name in REGISTRY_HEADERS[name]:
            if not (row.get(field_name) or "").strip() and (candidate.get(field_name) or "").strip():
                row[field_name] = candidate[field_name]
                changed = True
        if changed:
            updated += 1
        else:
            unchanged += 1
    return RegistrySync(name, candidates, rows, added, updated, unchanged, conflicts)


def serialize_registry(name: str, rows: list[dict[str, str]]) -> bytes:
    buffer = io.StringIO(newline="")
    writer = csv.DictWriter(buffer, fieldnames=REGISTRY_HEADERS[name])
    writer.writeheader()
    writer.writerows(rows)
    return b"\xef\xbb\xbf" + buffer.getvalue().encode("utf-8")


def write_fsynced(path: Path, data: bytes) -> None:
    with path.open("wb") as handle:
        handle.write(data)
        handle.flush()
        os.fsync(handle.fileno())


def cleanup_entry(qc_dir: Path, entry: dict[str, object]) -> None:
    for field_name in ("backup", "temporary"):
        value = str(entry.get(field_name) or "")
        if value:
            (qc_dir / value).unlink(missing_ok=True)


def rollback_entries(qc_dir: Path, entries: list[dict[str, object]]) -> None:
    for entry in reversed(entries):
        target = qc_dir / str(entry["target"])
        backup = qc_dir / str(entry["backup"])
        if bool(entry.get("had_original")) and backup.exists():
            os.replace(backup, target)
        elif not bool(entry.get("had_original")):
            target.unlink(missing_ok=True)
        cleanup_entry(qc_dir, entry)


def recover_transaction(qc_dir: Path) -> None:
    journal = qc_dir / TRANSACTION_NAME
    if not journal.exists():
        return
    try:
        payload = json.loads(journal.read_text(encoding="utf-8"))
        entries = payload.get("entries", [])
        if not isinstance(entries, list):
            raise ValueError("transaction entries must be a list")
        rollback_entries(qc_dir, entries)
    finally:
        journal.unlink(missing_ok=True)


def write_transaction(
    project: Path,
    registries: dict[str, RegistrySync],
    reports: dict[str, str],
    *,
    replace: Callable[[str | os.PathLike[str], str | os.PathLike[str]], None] = os.replace,
) -> None:
    qc_dir = project / QC_REL
    qc_dir.mkdir(parents=True, exist_ok=True)
    recover_transaction(qc_dir)
    token = uuid.uuid4().hex
    payloads: list[tuple[Path, bytes]] = []
    for name, registry in registries.items():
        payloads.append((qc_dir / name, serialize_registry(name, registry.merged_rows)))
    for name, content in reports.items():
        payloads.append((qc_dir / name, content.encode("utf-8")))

    entries: list[dict[str, object]] = []
    journal = qc_dir / TRANSACTION_NAME
    try:
        for target, data in payloads:
            temporary = qc_dir / f".{target.name}.{token}.temporary"
            backup = qc_dir / f".{target.name}.{token}.backup"
            write_fsynced(temporary, data)
            had_original = target.exists()
            if had_original:
                shutil.copy2(target, backup)
            entries.append({
                "target": target.name,
                "temporary": temporary.name,
                "backup": backup.name,
                "had_original": had_original,
            })
        write_fsynced(journal, json.dumps({"phase": "applying", "entries": entries}).encode("utf-8"))
        for entry in entries:
            replace(qc_dir / str(entry["temporary"]), qc_dir / str(entry["target"]))
    except Exception:
        rollback_entries(qc_dir, entries)
        journal.unlink(missing_ok=True)
        raise
    else:
        for entry in entries:
            cleanup_entry(qc_dir, entry)
        journal.unlink(missing_ok=True)


def summary_payload(summary: SyncSummary) -> dict[str, object]:
    return {
        "version": 1,
        "generated_at": datetime.now().isoformat(timespec="seconds"),
        "status": "conflict" if summary.counts.get("conflicts") else "candidates_synced",
        "project": str(summary.project),
        "counts": summary.counts,
        "warnings": summary.warnings,
        "ignored": summary.ignored,
        "registries": {
            name: {
                "discovered": len(registry.candidates),
                "added": registry.added,
                "updated": registry.updated,
                "unchanged": registry.unchanged,
                "conflicts": registry.conflicts,
            }
            for name, registry in summary.registries.items()
        },
    }


def render_reports(summary: SyncSummary) -> dict[str, str]:
    payload = summary_payload(summary)
    counts = summary.counts
    lines = [
        "# Contest QC Evidence Sync\n\n",
        "> 文件发现只生成待审核候选，不代表模型、结果或图表已经验证。\n\n",
        f"- status: `{payload['status']}`\n",
        f"- discovered: {counts['discovered']}\n",
        f"- added: {counts['added']}\n",
        f"- updated: {counts['updated']}\n",
        f"- unchanged: {counts['unchanged']}\n",
        f"- conflicts: {counts['conflicts']}\n",
        f"- ignored: {counts['ignored']}\n",
    ]
    if summary.warnings:
        lines.append("\n## Warnings\n\n")
        lines.extend(f"- {warning}\n" for warning in summary.warnings)
    return {
        "evidence_sync.json": json.dumps(payload, ensure_ascii=False, indent=2) + "\n",
        "evidence_sync.md": "".join(lines),
    }


def synchronize(project: Path, dry_run: bool = False) -> SyncSummary:
    project = project.expanduser().resolve()
    qc_dir = project / QC_REL
    if not dry_run:
        qc_dir.mkdir(parents=True, exist_ok=True)
        lock_path = qc_dir / LOCK_NAME
        with lock_path.open("a+") as lock:
            fcntl.flock(lock.fileno(), fcntl.LOCK_EX)
            recover_transaction(qc_dir)
            for name in TARGET_REGISTRIES:
                validate_header(qc_dir / name, REGISTRY_HEADERS[name])
            init_project(project)
            summary = build_sync(project)
            summary.registries = {
                name: merge_registry(name, registry.merged_rows, registry.candidates)
                for name, registry in summary.registries.items()
            }
            _refresh_counts(summary)
            changed = {
                name: registry
                for name, registry in summary.registries.items()
                if registry.added or registry.updated
            }
            write_transaction(project, changed, render_reports(summary))
            return summary
    summary = build_sync(project)
    summary.registries = {
        name: merge_registry(name, registry.merged_rows, registry.candidates)
        for name, registry in summary.registries.items()
    }
    _refresh_counts(summary)
    return summary


def _refresh_counts(summary: SyncSummary) -> None:
    summary.counts.update({
        "added": sum(registry.added for registry in summary.registries.values()),
        "updated": sum(registry.updated for registry in summary.registries.values()),
        "unchanged": sum(registry.unchanged for registry in summary.registries.values()),
        "conflicts": sum(len(registry.conflicts) for registry in summary.registries.values()),
    })


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Discover and conservatively merge review-only Contest QC evidence candidates."
    )
    parser.add_argument("project")
    parser.add_argument("--dry-run", action="store_true", help="Print discovery counts without writing files")
    args = parser.parse_args()
    project = Path(args.project).expanduser().resolve()
    if not project.is_dir():
        print(f"Project not found: {project}", file=sys.stderr)
        return 2
    try:
        summary = synchronize(project, dry_run=args.dry_run)
    except (RegistrySchemaError, json.JSONDecodeError, OSError, ValueError) as exc:
        print(str(exc), file=sys.stderr)
        return 2
    counts = summary.counts
    label = "Dry-run candidates" if args.dry_run else "Candidates synced"
    print(
        f"{label}: discovered={counts['discovered']}, added={counts['added']}, "
        f"updated={counts['updated']}, unchanged={counts['unchanged']}, "
        f"conflicts={counts['conflicts']}, ignored={counts['ignored']}"
    )
    return 1 if counts["conflicts"] else 0


if __name__ == "__main__":
    raise SystemExit(main())
