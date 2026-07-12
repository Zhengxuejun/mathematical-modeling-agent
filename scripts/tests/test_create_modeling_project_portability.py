from __future__ import annotations

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
    assert (project / "06_过程记录" / "竞赛质控" / "deliverable_matrix.csv").is_file()
