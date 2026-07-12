from __future__ import annotations

import sys
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parents[1]
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))

from finalize_modeling_project import DEFAULT_DIRS, build_submission_package
from submission_package_contract import validate_submission_package


def make_finalizable_project(tmp_path: Path) -> Path:
    project = tmp_path / "project"
    for directory in DEFAULT_DIRS:
        (project / directory).mkdir(parents=True, exist_ok=True)
    (project / "05_报告定稿/report.md").write_text(
        "# Competition report\n\n## Question 1\nThe verified result is 1.\n",
        encoding="utf-8",
    )
    (project / "02_代码/model.py").write_text("print(1)\n", encoding="utf-8")
    (project / "01_原始数据/input.csv").write_text("id,value\na,1\n", encoding="utf-8")
    (project / "03_结果表格/model_results.csv").write_text(
        "metric,value\nobjective,1\n",
        encoding="utf-8",
    )
    return project


def test_second_run_does_not_retain_disabled_payload(tmp_path: Path) -> None:
    project = make_finalizable_project(tmp_path)
    first = build_submission_package(
        project,
        entry="02_代码/model.py",
        include_code=True,
        include_raw_data=True,
    )
    assert first.published
    assert (project / "07_提交包/source_code/model.py").exists()
    assert (project / "07_提交包/raw_data/input.csv").exists()

    second = build_submission_package(
        project,
        entry=None,
        include_code=False,
        include_raw_data=False,
    )
    assert second.published
    assert not (project / "07_提交包/source_code").exists()
    assert not (project / "07_提交包/raw_data").exists()
    assert validate_submission_package(project / "07_提交包").valid


def test_failed_rebuild_preserves_previous_valid_package(tmp_path: Path) -> None:
    project = make_finalizable_project(tmp_path)
    first = build_submission_package(project, entry="02_代码/model.py")
    assert first.published
    manifest_path = project / "07_提交包/submission_manifest.json"
    old_manifest = manifest_path.read_bytes()

    (project / "05_报告定稿/report.md").unlink()
    failed = build_submission_package(project, entry="02_代码/model.py")

    assert not failed.published
    assert any(check.name == "report_exists" and check.status == "fail" for check in failed.checks)
    assert manifest_path.read_bytes() == old_manifest
    assert validate_submission_package(project / "07_提交包").valid


def test_published_manifest_and_checksums_match_payload(tmp_path: Path) -> None:
    project = make_finalizable_project(tmp_path)
    result = build_submission_package(project, entry="02_代码/model.py")

    assert result.published
    validation = validate_submission_package(project / "07_提交包")
    assert validation.valid, validation.reasons
    assert "report.md" in validation.checked_files
    assert not list(project.glob("07_提交包.staging-*"))
    assert not list(project.glob("07_提交包.backup-*"))
