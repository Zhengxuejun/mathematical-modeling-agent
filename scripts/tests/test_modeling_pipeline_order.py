from __future__ import annotations

import sys
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parents[1]
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))

from modeling_pipeline import pipeline_step_names


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
