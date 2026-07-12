from __future__ import annotations

import fcntl
import json
import os
from contextlib import contextmanager
from pathlib import Path
from typing import Any, Callable, Iterator

from .contracts import TreeError, load_json_object, validate_tree
from .reporting import render_tree

TREE_RELATIVE_DIR = Path("06_过程记录/候选方案树")


def tree_directory(project: Path) -> Path:
    return project.resolve() / TREE_RELATIVE_DIR


@contextmanager
def tree_lock(project: Path) -> Iterator[None]:
    directory = tree_directory(project)
    directory.mkdir(parents=True, exist_ok=True)
    lock_path = directory / "candidate_tree.lock"
    with lock_path.open("a+", encoding="utf-8") as handle:
        fcntl.flock(handle.fileno(), fcntl.LOCK_EX)
        try:
            yield
        finally:
            fcntl.flock(handle.fileno(), fcntl.LOCK_UN)


def load_tree(project: Path) -> dict[str, Any]:
    path = tree_directory(project) / "candidate_tree.json"
    if not path.is_file():
        raise TreeError("candidate tree is not initialized")
    tree = load_json_object(path)
    validate_tree(tree)
    return tree


def initialize(project: Path, tree: dict[str, Any]) -> None:
    if not project.resolve().is_dir():
        raise TreeError(f"project directory does not exist: {project}")
    with tree_lock(project):
        if (tree_directory(project) / "candidate_tree.json").exists():
            raise TreeError("candidate tree is already initialized")
        save_tree(project, tree)


def mutate(project: Path, callback: Callable[[dict[str, Any]], Any]) -> tuple[dict[str, Any], Any]:
    with tree_lock(project):
        tree = load_tree(project)
        result = callback(tree)
        validate_tree(tree)
        save_tree(project, tree)
        return tree, result


def save_tree(project: Path, tree: dict[str, Any]) -> None:
    validate_tree(tree)
    directory = tree_directory(project)
    directory.mkdir(parents=True, exist_ok=True)
    payloads = {
        directory / "candidate_tree.json": json.dumps(tree, ensure_ascii=False, indent=2, sort_keys=True, allow_nan=False) + "\n",
        directory / "candidate_tree.md": render_tree(tree),
    }
    for target, content in payloads.items():
        temporary = target.with_name(f".{target.name}.{os.getpid()}.tmp")
        with temporary.open("w", encoding="utf-8", newline="\n") as handle:
            handle.write(content)
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temporary, target)
    directory_fd = os.open(directory, os.O_RDONLY)
    try:
        os.fsync(directory_fd)
    finally:
        os.close(directory_fd)
