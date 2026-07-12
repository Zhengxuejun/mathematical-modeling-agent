#!/usr/bin/env python3
"""Validate the on-disk contract for a published submission package."""
from __future__ import annotations

import hashlib
import json
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any

PACKAGE_SCHEMA_VERSION = "2.0"
CHECKSUM_FILE = "SHA256SUMS.txt"
REQUIRED_CONTROL_FILES = {
    "README_submit.md",
    "submission_manifest.json",
    CHECKSUM_FILE,
}


@dataclass
class PackageValidation:
    valid: bool
    reasons: list[str]
    checked_files: list[str]


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _safe_package_path(package_dir: Path, value: Any) -> tuple[str, Path] | None:
    if not isinstance(value, str) or not value.strip():
        return None
    raw = value.strip().replace("\\", "/")
    relative = Path(raw)
    if relative.is_absolute() or raw in {".", ".."}:
        return None
    root = package_dir.resolve()
    try:
        candidate = (root / relative).resolve(strict=False)
        normalized = candidate.relative_to(root).as_posix()
    except (OSError, RuntimeError, ValueError):
        return None
    if normalized in {"", "."}:
        return None
    return normalized, candidate


def write_checksums(package_dir: Path, relative_paths: list[str]) -> Path:
    lines: list[str] = []
    for value in sorted(set(relative_paths)):
        resolved = _safe_package_path(package_dir, value)
        if resolved is None:
            raise ValueError(f"unsafe package path: {value!r}")
        normalized, path = resolved
        if not path.is_file():
            raise FileNotFoundError(f"missing package file: {normalized}")
        lines.append(f"{sha256_file(path)}  {normalized}\n")
    checksum_path = package_dir / CHECKSUM_FILE
    checksum_path.write_text("".join(lines), encoding="utf-8")
    return checksum_path


def parse_checksums(path: Path) -> tuple[dict[str, str], list[str]]:
    records: dict[str, str] = {}
    errors: list[str] = []
    try:
        lines = path.read_text(encoding="utf-8").splitlines()
    except Exception as exc:
        return {}, [f"cannot read checksum file: {exc}"]
    for index, line in enumerate(lines, start=1):
        match = re.fullmatch(r"([0-9a-fA-F]{64})  (.+)", line)
        if not match:
            errors.append(f"malformed checksum line {index}")
            continue
        digest, relative = match.groups()
        if relative in records:
            errors.append(f"duplicate checksum path: {relative}")
            continue
        records[relative] = digest.lower()
    return records, errors


def _load_manifest(path: Path) -> tuple[dict[str, Any], list[str]]:
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except Exception as exc:
        return {}, [f"invalid submission manifest: {exc}"]
    if not isinstance(payload, dict):
        return {}, ["submission manifest must be a JSON object"]
    return payload, []


def validate_submission_package(package_dir: Path) -> PackageValidation:
    package_dir = package_dir.expanduser()
    reasons: list[str] = []
    checked_files: list[str] = []
    if not package_dir.is_dir():
        return PackageValidation(False, [f"package directory missing: {package_dir}"], [])

    for relative in sorted(REQUIRED_CONTROL_FILES):
        if not (package_dir / relative).is_file():
            reasons.append(f"missing control file: {relative}")
    manifest_path = package_dir / "submission_manifest.json"
    checksum_path = package_dir / CHECKSUM_FILE
    if not manifest_path.is_file():
        return PackageValidation(False, reasons, checked_files)

    manifest, manifest_errors = _load_manifest(manifest_path)
    reasons.extend(manifest_errors)
    if manifest_errors:
        return PackageValidation(False, reasons, checked_files)

    if manifest.get("schema_version") != PACKAGE_SCHEMA_VERSION:
        reasons.append(
            f"unsupported manifest schema: {manifest.get('schema_version')!r}; "
            f"expected {PACKAGE_SCHEMA_VERSION}"
        )
    if manifest.get("package_valid") is not True:
        reasons.append("manifest package_valid is not true")

    counts = manifest.get("validation_counts")
    fail_count = counts.get("fail") if isinstance(counts, dict) else None
    if fail_count != 0:
        reasons.append(f"manifest reports failed checks: {fail_count!r}")
    checks = manifest.get("checks")
    if not isinstance(checks, list):
        reasons.append("manifest checks must be a list")
    elif any(isinstance(check, dict) and check.get("status") == "fail" for check in checks):
        reasons.append("manifest contains failed checks")

    package_files = manifest.get("package_files")
    if not isinstance(package_files, list) or not package_files:
        reasons.append("manifest package_files must be a non-empty list")
        package_files = []

    normalized_files: list[str] = []
    for value in package_files:
        resolved = _safe_package_path(package_dir, value)
        if resolved is None:
            reasons.append(f"unsafe package path: {value!r}")
            continue
        normalized, path = resolved
        if normalized == CHECKSUM_FILE:
            reasons.append(f"checksum file must not hash itself: {CHECKSUM_FILE}")
            continue
        if normalized in normalized_files:
            reasons.append(f"duplicate package file: {normalized}")
            continue
        normalized_files.append(normalized)
        if not path.is_file():
            reasons.append(f"missing package file: {normalized}")

    for required in ("README_submit.md", "submission_manifest.json"):
        if required not in normalized_files:
            reasons.append(f"manifest package_files missing control file: {required}")

    actual_files = {
        path.relative_to(package_dir).as_posix()
        for path in package_dir.rglob("*")
        if path.is_file() and path.name != CHECKSUM_FILE
    }
    listed_files = set(normalized_files)
    for relative in sorted(actual_files - listed_files):
        reasons.append(f"unexpected package file: {relative}")

    if checksum_path.is_file():
        checksums, checksum_errors = parse_checksums(checksum_path)
        reasons.extend(checksum_errors)
        for relative in sorted(set(checksums) - listed_files):
            reasons.append(f"checksum references unlisted file: {relative}")
        for relative in normalized_files:
            resolved = _safe_package_path(package_dir, relative)
            if resolved is None:
                continue
            _, path = resolved
            expected = checksums.get(relative)
            if expected is None:
                reasons.append(f"missing checksum: {relative}")
                continue
            if not path.is_file():
                continue
            actual = sha256_file(path)
            if actual != expected:
                reasons.append(f"checksum mismatch: {relative}")
                continue
            checked_files.append(relative)

    return PackageValidation(not reasons, reasons, checked_files)
