from __future__ import annotations

import hashlib
from pathlib import Path, PurePosixPath


class PathValidationError(ValueError):
    pass


def validate_relative_path(value: str) -> PurePosixPath:
    if not isinstance(value, str) or not value or "\\" in value:
        raise PathValidationError(f"unsafe relative path: {value!r}")
    path = PurePosixPath(value)
    if path.is_absolute() or any(part in {"", ".", ".."} for part in path.parts):
        raise PathValidationError(f"unsafe relative path: {value!r}")
    return path


def resolve_local_file(root: Path, value: str, *, required: bool = True) -> Path:
    relative = validate_relative_path(value)
    root = root.resolve()
    candidate = root.joinpath(*relative.parts)
    try:
        resolved = candidate.resolve(strict=required)
    except FileNotFoundError as exc:
        raise PathValidationError(f"missing file: {value}") from exc
    try:
        resolved.relative_to(root)
    except ValueError as exc:
        raise PathValidationError(f"path escapes root: {value}") from exc
    if required and not resolved.is_file():
        raise PathValidationError(f"not a file: {value}")
    return resolved


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()

