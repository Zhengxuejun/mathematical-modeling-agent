from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parents[1]
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))

from create_modeling_project import create_project


def test_scaffold_wrappers_resolve_the_current_installed_skill_path(tmp_path: Path) -> None:
    project = create_project("portable-skill", tmp_path)
    wrapper = (project / "02_代码" / "08_pipeline.py").read_text(encoding="utf-8")
    expected = str(SCRIPT_DIR / "modeling_pipeline.py")
    assert expected in wrapper
    assert "__SKILL_SCRIPT_DIR__" not in wrapper
    source = (SCRIPT_DIR / "create_modeling_project.py").read_text(encoding="utf-8")
    assert "__SKILL_SCRIPT_DIR__" in source
    assert "Path('__SKILL_SCRIPT_DIR__/modeling_pipeline.py')" in source
    assert (project / "02_代码" / "17_contest_qc.py").is_file()
    evidence_sync = project / "02_代码" / "18_contest_evidence_sync.py"
    assert evidence_sync.is_file()
    evidence_sync_text = evidence_sync.read_text(encoding="utf-8")
    assert str(SCRIPT_DIR / "contest_evidence_sync.py") in evidence_sync_text
    assert "__SKILL_SCRIPT_DIR__" not in evidence_sync_text
    metadata = json.loads((project / "project_meta.json").read_text(encoding="utf-8"))
    assert metadata["contest_evidence_sync"] == "02_代码/18_contest_evidence_sync.py"
    candidate_tree = project / "02_代码" / "19_candidate_solution_tree.py"
    assert candidate_tree.is_file()
    candidate_tree_text = candidate_tree.read_text(encoding="utf-8")
    assert str(SCRIPT_DIR / "candidate_solution_tree.py") in candidate_tree_text
    assert "__SKILL_SCRIPT_DIR__" not in candidate_tree_text
    assert metadata["candidate_solution_tree"] == "02_代码/19_candidate_solution_tree.py"
    assert (project / "08_候选方案" / "README.md").is_file()
    initialized = subprocess.run(
        [sys.executable, str(candidate_tree), "init", "--objective-metric", "objective", "--direction", "maximize"],
        text=True,
        capture_output=True,
    )
    assert initialized.returncode == 0, initialized.stdout + initialized.stderr
    assert (project / "06_过程记录/候选方案树/candidate_tree.json").is_file()
    assert (project / "06_过程记录" / "竞赛质控" / "deliverable_matrix.csv").is_file()
