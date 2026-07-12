from __future__ import annotations

import hashlib
import json
import sys
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parents[1]
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))

from submission_package_contract import validate_submission_package
from update_project_state import infer_states


def digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def make_package(
    package: Path,
    *,
    package_valid: bool = True,
    failed_checks: int = 0,
    package_files: list[str] | None = None,
) -> Path:
    package.mkdir(parents=True, exist_ok=True)
    (package / "README_submit.md").write_text("# Submission\n", encoding="utf-8")
    (package / "report.md").write_text("# Current report\nresult=1\n", encoding="utf-8")
    files = package_files or ["README_submit.md", "report.md", "submission_manifest.json"]
    manifest = {
        "schema_version": "2.0",
        "package_valid": package_valid,
        "validation_counts": {"fail": failed_checks, "warn": 0, "pass": 2},
        "checks": ([{"name": "report", "status": "fail", "detail": "missing"}] if failed_checks else []),
        "copied_files": ["report.md"],
        "package_files": files,
        "checksum_algorithm": "sha256",
        "checksum_file": "SHA256SUMS.txt",
    }
    (package / "submission_manifest.json").write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    checksum_lines = []
    for relative in files:
        path = package / relative
        if path.is_file():
            checksum_lines.append(f"{digest(path)}  {relative}\n")
    (package / "SHA256SUMS.txt").write_text("".join(checksum_lines), encoding="utf-8")
    return package


def test_valid_package_passes_validation(tmp_path: Path) -> None:
    package = make_package(tmp_path / "package")
    result = validate_submission_package(package)
    assert result.valid
    assert result.reasons == []
    assert "submission_manifest.json" in result.checked_files


def test_failed_manifest_blocks_package(tmp_path: Path) -> None:
    package = make_package(tmp_path / "package", package_valid=False, failed_checks=1)
    result = validate_submission_package(package)
    assert not result.valid
    assert any("package_valid" in reason for reason in result.reasons)
    assert any("failed checks" in reason for reason in result.reasons)


def test_checksum_corruption_blocks_package(tmp_path: Path) -> None:
    package = make_package(tmp_path / "package")
    (package / "report.md").write_text("corrupted", encoding="utf-8")
    result = validate_submission_package(package)
    assert not result.valid
    assert any("checksum mismatch" in reason for reason in result.reasons)


def test_missing_payload_blocks_package(tmp_path: Path) -> None:
    package = make_package(tmp_path / "package")
    (package / "report.md").unlink()
    result = validate_submission_package(package)
    assert not result.valid
    assert any("missing package file" in reason for reason in result.reasons)


def test_unsafe_manifest_path_blocks_package(tmp_path: Path) -> None:
    package = make_package(
        tmp_path / "package",
        package_files=["README_submit.md", "../outside.txt", "submission_manifest.json"],
    )
    result = validate_submission_package(package)
    assert not result.valid
    assert any("unsafe package path" in reason for reason in result.reasons)


def test_legacy_manifest_without_explicit_validity_is_rejected(tmp_path: Path) -> None:
    package = make_package(tmp_path / "package")
    manifest_path = package / "submission_manifest.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    del manifest["package_valid"]
    manifest_path.write_text(json.dumps(manifest) + "\n", encoding="utf-8")
    result = validate_submission_package(package)
    assert not result.valid
    assert any("package_valid" in reason for reason in result.reasons)


def test_s8_requires_valid_manifest_and_checksums(tmp_path: Path) -> None:
    project = tmp_path / "project"
    make_package(project / "07_提交包", package_valid=False, failed_checks=1)
    s8 = infer_states(project)[8]
    assert not s8.complete
    assert any("package_valid" in item or "failed" in item for item in s8.evidence_missing)


def test_s8_accepts_verified_package(tmp_path: Path) -> None:
    project = tmp_path / "project"
    make_package(project / "07_提交包")
    s8 = infer_states(project)[8]
    assert s8.complete
    assert any(item.endswith("submission_manifest.json") for item in s8.evidence_found)
