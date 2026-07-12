from __future__ import annotations

import hashlib
from pathlib import Path, PurePosixPath

from .contracts import TreeError


def safe_relative_path(value: str) -> PurePosixPath:
    if not isinstance(value, str) or not value or "\\" in value:
        raise TreeError(f"unsafe relative path: {value!r}")
    path = PurePosixPath(value)
    if path.is_absolute() or any(part in {"", ".", ".."} for part in path.parts):
        raise TreeError(f"unsafe relative path: {value!r}")
    return path


def resolve_project_path(project: Path, value: str, *, directory: bool) -> Path:
    relative = safe_relative_path(value)
    root = project.resolve(strict=True)
    try:
        resolved = root.joinpath(*relative.parts).resolve(strict=True)
        resolved.relative_to(root)
    except (FileNotFoundError, ValueError) as exc:
        raise TreeError(f"path is missing or escapes project: {value}") from exc
    if directory and not resolved.is_dir():
        raise TreeError(f"not a directory: {value}")
    if not directory and not resolved.is_file():
        raise TreeError(f"not a file: {value}")
    return resolved


def project_relative(project: Path, path: Path) -> str:
    try:
        return path.resolve(strict=True).relative_to(project.resolve(strict=True)).as_posix()
    except (FileNotFoundError, ValueError) as exc:
        raise TreeError(f"path is outside project: {path}") from exc


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()
