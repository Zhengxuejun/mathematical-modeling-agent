from __future__ import annotations

import sys
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parents[1]
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))

from modeling_pipeline import StepResult, current_competition_summary, pipeline_step_names


def test_full_pipeline_packages_after_report_and_competition_gates() -> None:
    names = pipeline_step_names(skeleton_only=False)
    assert names.index("problem_coverage") < names.index("result_interpretation")
    assert names.index("result_interpretation") < names.index("report_assembly")
    assert names.index("report_assembly") < names.index("report_audit")
    assert names.index("report_audit") < names.index("contest_evidence_sync")
    assert names.index("contest_evidence_sync") < names.index("contest_qc")
    assert names.index("contest_qc") < names.index("competition_readiness")
    assert names.index("competition_readiness") < names.index("finalize")
    assert names.index("finalize") < names.index("state_update_final")


def test_skeleton_pipeline_never_packages() -> None:
    names = pipeline_step_names(skeleton_only=True)
    assert names == [
        "data_audit",
        "model_skeleton",
        "domain_checker_templates",
        "quality_gate",
        "state_update_pre_finalize",
    ]
    assert "finalize" not in names
    assert "state_update_final" not in names


def test_failed_readiness_step_cannot_reuse_previous_true(tmp_path: Path) -> None:
    output = tmp_path / "competition_readiness.json"
    output.write_text('{"readiness":"competition_ready","competition_ready":true}\n', encoding="utf-8")
    failed = StepResult(
        name="competition_readiness",
        command=["python", "competition_readiness_gate.py"],
        exit_code=9,
        duration_sec=0.1,
        stdout_tail="",
        stderr_tail="failed before writing output",
    )

    assert current_competition_summary(failed, output) == {}
