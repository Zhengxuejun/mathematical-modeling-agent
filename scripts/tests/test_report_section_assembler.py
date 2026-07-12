from __future__ import annotations

import sys
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parents[1]
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))

from report_section_assembler import write_outputs


def assembly_summary(project: Path) -> dict:
    return {
        "generated_at": "2026-01-01T00:00:00",
        "project": str(project),
        "title": "Competition report",
        "counts": {
            "questions": 0,
            "ready_sections": 0,
            "partial_sections": 0,
            "weak_sections": 0,
            "tables_inventory": 0,
            "figures_inventory": 0,
            "raw_data_refs": 0,
            "warn": 0,
            "fail": 0,
        },
        "global_warnings": [],
        "raw_data_files": [],
        "raw_data_refs": [],
        "sections": [],
    }


def test_report_assembly_preserves_existing_human_edited_report(tmp_path: Path) -> None:
    report = tmp_path / "05_报告定稿/report_draft.md"
    report.parent.mkdir(parents=True)
    human_content = "# Final report\n\nVerified model and conclusions.\n"
    report.write_text(human_content, encoding="utf-8")

    write_outputs(tmp_path, assembly_summary(tmp_path), "report_draft.md")

    assert report.read_text(encoding="utf-8") == human_content


def test_report_assembly_can_explicitly_replace_existing_draft(tmp_path: Path) -> None:
    report = tmp_path / "05_报告定稿/report_draft.md"
    report.parent.mkdir(parents=True)
    report.write_text("human content", encoding="utf-8")

    write_outputs(tmp_path, assembly_summary(tmp_path), "report_draft.md", overwrite_report=True)

    assert report.read_text(encoding="utf-8") != "human content"
