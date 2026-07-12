from __future__ import annotations

import json
import sys
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parents[1]
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))

from repair_advisor import build


def write_json(path: Path, payload: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload), encoding="utf-8")


def test_prefinal_repair_ignores_previous_package_manifest(tmp_path: Path) -> None:
    write_json(tmp_path / "06_过程记录/pipeline/pipeline_run_summary.json", {
        "phase": "pre_finalize",
        "recommended_status": "in_progress",
        "highest_contiguous_state": "S7",
        "steps": [],
    })
    write_json(tmp_path / "07_提交包/submission_manifest.json", {
        "checks": [{"name": "old_failure", "status": "fail", "detail": "stale"}],
    })

    summary = build(tmp_path)

    assert summary["counts"]["fail"] == 0
    assert not any(item["source"] == "submission_manifest" for item in summary["advice"])
