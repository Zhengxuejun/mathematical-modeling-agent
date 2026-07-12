from __future__ import annotations

import json
import math
import re
from pathlib import Path
from typing import Any

from . import TREE_VERSION

TREE_SCHEMA_VERSION = 1
CANDIDATE_ID_RE = re.compile(r"C[0-9]{3}")
STATUSES = {"registered", "evaluated", "blocked", "selected"}


class TreeError(ValueError):
    pass


def load_json_object(path: Path) -> dict[str, Any]:
    try:
        value = json.loads(
            path.read_text(encoding="utf-8"),
            parse_constant=lambda token: (_ for _ in ()).throw(ValueError(token)),
        )
    except (OSError, UnicodeError, json.JSONDecodeError, ValueError) as exc:
        raise TreeError(f"cannot read valid JSON from {path}: {exc}") from exc
    if not isinstance(value, dict):
        raise TreeError(f"JSON root must be an object: {path}")
    reject_non_finite(value)
    return value


def reject_non_finite(value: Any, location: str = "root") -> None:
    if isinstance(value, float) and not math.isfinite(value):
        raise TreeError(f"non-finite number at {location}")
    if isinstance(value, dict):
        for key, item in value.items():
            reject_non_finite(item, f"{location}.{key}")
    elif isinstance(value, list):
        for index, item in enumerate(value):
            reject_non_finite(item, f"{location}[{index}]")


def new_tree(
    objective_metric: str,
    direction: str,
    validation_metric: str,
    max_candidates: int,
    max_depth: int,
) -> dict[str, Any]:
    tree = {
        "schema_version": TREE_SCHEMA_VERSION,
        "tool_version": TREE_VERSION,
        "objective_metric": objective_metric,
        "direction": direction,
        "validation_metric": validation_metric,
        "max_candidates": max_candidates,
        "max_depth": max_depth,
        "selected_candidate_id": None,
        "selection_ranking": [],
        "nodes": [],
    }
    validate_tree(tree)
    return tree


def validate_tree(tree: dict[str, Any]) -> None:
    if tree.get("schema_version") != TREE_SCHEMA_VERSION:
        raise TreeError("candidate tree schema_version must be 1")
    if not isinstance(tree.get("tool_version"), str) or not tree["tool_version"]:
        raise TreeError("candidate tree tool_version must be a non-empty string")
    for field in ("objective_metric", "validation_metric"):
        if not isinstance(tree.get(field), str) or not tree[field].strip():
            raise TreeError(f"{field} must be a non-empty string")
    if tree.get("direction") not in {"maximize", "minimize"}:
        raise TreeError("direction must be maximize or minimize")
    for field in ("max_candidates", "max_depth"):
        if not isinstance(tree.get(field), int) or isinstance(tree[field], bool) or tree[field] < 1:
            raise TreeError(f"{field} must be a positive integer")
    nodes = tree.get("nodes")
    if not isinstance(nodes, list) or len(nodes) > tree["max_candidates"]:
        raise TreeError("nodes must be a list within max_candidates")
    by_id: dict[str, dict[str, Any]] = {}
    submissions: set[str] = set()
    for node in nodes:
        if not isinstance(node, dict):
            raise TreeError("every candidate node must be an object")
        candidate_id = node.get("candidate_id")
        if not isinstance(candidate_id, str) or not CANDIDATE_ID_RE.fullmatch(candidate_id) or candidate_id in by_id:
            raise TreeError(f"invalid or duplicate candidate id: {candidate_id!r}")
        if node.get("status") not in STATUSES:
            raise TreeError(f"invalid candidate status: {candidate_id}")
        for field in ("submission_path", "label", "hypothesis"):
            if not isinstance(node.get(field), str) or not node[field].strip():
                raise TreeError(f"candidate {candidate_id} has invalid {field}")
        if node["submission_path"] in submissions:
            raise TreeError(f"duplicate candidate submission: {node['submission_path']}")
        submissions.add(node["submission_path"])
        parent = node.get("parent_id")
        if parent is not None and parent not in by_id:
            raise TreeError(f"candidate {candidate_id} has unknown or forward parent")
        expected_depth = 0 if parent is None else int(by_id[parent]["depth"]) + 1
        if node.get("depth") != expected_depth or expected_depth > tree["max_depth"]:
            raise TreeError(f"candidate {candidate_id} has invalid depth")
        evaluation = node.get("evaluation")
        if evaluation is not None and not isinstance(evaluation, dict):
            raise TreeError(f"candidate {candidate_id} has invalid evaluation")
        if evaluation is not None:
            _validate_evaluation(candidate_id, evaluation)
        if node["status"] == "registered" and evaluation is not None:
            raise TreeError(f"registered candidate {candidate_id} cannot have evaluation")
        if node["status"] in {"evaluated", "selected"} and (evaluation is None or evaluation.get("eligible") is not True):
            raise TreeError(f"eligible status is inconsistent for candidate {candidate_id}")
        if node["status"] == "blocked" and (evaluation is None or evaluation.get("eligible") is not False):
            raise TreeError(f"blocked status is inconsistent for candidate {candidate_id}")
        by_id[candidate_id] = node
    selected = tree.get("selected_candidate_id")
    selected_nodes = [node for node in nodes if node["status"] == "selected"]
    if selected is None and selected_nodes:
        raise TreeError("selected status exists without selected_candidate_id")
    if selected is not None:
        if selected not in by_id or len(selected_nodes) != 1 or selected_nodes[0]["candidate_id"] != selected:
            raise TreeError("selected_candidate_id is inconsistent with node status")
    if not isinstance(tree.get("selection_ranking"), list):
        raise TreeError("selection_ranking must be a list")
    ranking_ids: set[str] = set()
    for item in tree["selection_ranking"]:
        if not isinstance(item, dict) or set(item) != {"candidate_id", "comparison"}:
            raise TreeError("selection ranking entries need candidate_id and comparison")
        if item["candidate_id"] not in by_id or item["candidate_id"] in ranking_ids:
            raise TreeError("selection ranking contains unknown or duplicate candidate")
        if not isinstance(item["comparison"], str) or not item["comparison"]:
            raise TreeError("selection comparison must be a non-empty string")
        ranking_ids.add(item["candidate_id"])
    reject_non_finite(tree)


def _validate_evaluation(candidate_id: str, evaluation: dict[str, Any]) -> None:
    if not isinstance(evaluation.get("eligible"), bool):
        raise TreeError(f"candidate {candidate_id} evaluation needs eligible boolean")
    gates = evaluation.get("gates")
    if not isinstance(gates, dict) or not gates or any(not isinstance(key, str) or not isinstance(value, bool) for key, value in gates.items()):
        raise TreeError(f"candidate {candidate_id} has invalid gates")
    if evaluation["eligible"] != all(gates.values()):
        raise TreeError(f"candidate {candidate_id} eligibility disagrees with gates")
    reasons = evaluation.get("blocking_reasons")
    if not isinstance(reasons, list) or any(not isinstance(item, str) or not item for item in reasons):
        raise TreeError(f"candidate {candidate_id} has invalid blocking reasons")
    if evaluation["eligible"] and reasons:
        raise TreeError(f"eligible candidate {candidate_id} cannot have blocking reasons")
    if not evaluation["eligible"] and not reasons:
        raise TreeError(f"blocked candidate {candidate_id} needs a blocking reason")
    for field in ("objective", "validation_score", "runtime_seconds"):
        value = evaluation.get(field)
        if value is not None and (not isinstance(value, (int, float)) or isinstance(value, bool) or not math.isfinite(value)):
            raise TreeError(f"candidate {candidate_id} has invalid {field}")
    validation = evaluation.get("validation_score")
    if validation is not None and not 0 <= validation <= 1:
        raise TreeError(f"candidate {candidate_id} validation_score is outside [0, 1]")
    runtime = evaluation.get("runtime_seconds")
    if runtime is not None and runtime < 0:
        raise TreeError(f"candidate {candidate_id} runtime_seconds is negative")
    for field in ("verified_evidence", "verified_inputs", "submission_hashes"):
        mapping = evaluation.get(field)
        if not isinstance(mapping, dict) or any(not isinstance(key, str) or not isinstance(value, str) for key, value in mapping.items()):
            raise TreeError(f"candidate {candidate_id} has invalid {field}")
    benchmark = evaluation.get("benchmark")
    if benchmark is not None:
        if not isinstance(benchmark, dict):
            raise TreeError(f"candidate {candidate_id} has invalid benchmark")
        for field in ("case_id", "case_hash", "verdict"):
            if not isinstance(benchmark.get(field), str):
                raise TreeError(f"candidate {candidate_id} benchmark lacks {field}")
        score = benchmark.get("total_score")
        if not isinstance(score, (int, float)) or isinstance(score, bool) or not math.isfinite(score) or not 0 <= score <= 100:
            raise TreeError(f"candidate {candidate_id} has invalid benchmark score")
        blocks = benchmark.get("hard_blocks")
        if not isinstance(blocks, list) or any(not isinstance(item, str) for item in blocks):
            raise TreeError(f"candidate {candidate_id} has invalid benchmark hard blocks")
