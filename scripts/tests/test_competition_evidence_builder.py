from __future__ import annotations

import json
import sys
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parents[1]
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))

from competition_evidence_builder import detect_domain_checker_implementation


def test_generated_template_does_not_downgrade_independent_passing_checker(tmp_path: Path) -> None:
    generated = tmp_path / "02_代码/generated_checkers/check_optimization.py"
    generated.parent.mkdir(parents=True)
    generated.write_text("# TODO: template requires project-specific checks\n", encoding="utf-8")
    implemented = tmp_path / "02_代码/check_constraints.py"
    implemented.write_text("def check_capacity():\n    return True\n", encoding="utf-8")
    output_dir = tmp_path / "06_过程记录/领域checker"
    output_dir.mkdir(parents=True)
    (output_dir / "domain_checker_templates.json").write_text(
        json.dumps({"checker_files": ["02_代码/generated_checkers/check_optimization.py"]}),
        encoding="utf-8",
    )
    (output_dir / "domain_checker_final.json").write_text(
        json.dumps({
            "checker_type": "domain_checker",
            "issue_count": 0,
            "warn_count": 0,
            "checks": [{"id": "capacity", "status": "pass"}],
        }),
        encoding="utf-8",
    )

    result = detect_domain_checker_implementation(tmp_path, [generated, implemented])

    assert result["status"] == "implemented_checker_pass"
    assert result["issue_count"] == 0
    assert "02_代码/check_constraints.py" in result["implemented_checker_files"]
