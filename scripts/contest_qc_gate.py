#!/usr/bin/env python3
"""Contest-quality contract and evidence gate for modeling projects.

This is a deliberately small, executable integration of the high-value parts of
an expert contest-QC workflow: a current-question lock, deliverable tracking,
real-data PoCs, model/code handoff, mathematical checks, reproducible runs,
evidence-backed claims/figures, judge-risk findings, and final compliance.

It never certifies an award. It writes reviewable evidence under
``06_过程记录/竞赛质控`` and reports one of:
- ``blocked``: a required evidence chain is absent or contradicted;
- ``needs_review``: no hard block, but required review evidence is incomplete;
- ``early_ready`` / ``model_ready`` / ``final_ready``: the selected phase has
  the required machine-checkable evidence. Human modeling judgement still
  remains necessary.
"""
from __future__ import annotations

import argparse
import csv
import fcntl
import hashlib
import io
import json
import os
import re
import sys
import tempfile
from contextlib import contextmanager
from dataclasses import asdict, dataclass
from datetime import datetime
from pathlib import Path
from typing import Any, Iterator

QC_REL = Path("06_过程记录") / "竞赛质控"

REGISTRY_HEADERS: dict[str, list[str]] = {
    "deliverable_matrix.csv": [
        "deliverable_id", "problem_id", "subquestion", "required_output", "format",
        "evidence_needed", "owner", "status", "risk_note", "approval_source", "omission_reason", "accepted_by",
    ],
    "symbol_table.csv": ["symbol", "type", "meaning", "unit", "domain", "source", "status"],
    "assumption_log.csv": [
        "assumption_id", "statement", "affected_variables", "affected_constraints", "rationale",
        "validation_plan", "risk_if_false", "status",
    ],
    "poc_registry.csv": [
        "poc_id", "problem_id", "subquestion", "candidate_id", "model_version",
        "script_or_command", "source_data", "source_slice", "metric", "value", "unit",
        "runtime", "status", "failure_reason", "promoted_model_version", "notes",
    ],
    "math_verification.csv": [
        "check_id", "subquestion", "artifact", "location", "claim_id", "check_type",
        "input_ref", "expected_relation", "observed", "status", "severity", "minimum_fix", "owner",
    ],
    "run_record.csv": [
        "run_id", "problem_id", "model_version", "command", "entry_script", "input_files",
        "parameters", "seed", "solver", "solver_status", "warnings", "output_tables",
        "output_figures", "log_path", "started_at", "completed_at", "run_status", "superseded_by", "notes",
    ],
    "artifact_manifest.csv": [
        "artifact_id", "run_id", "role", "path", "sha256", "bytes", "frozen_at", "status", "notes",
    ],
    "result_registry.csv": [
        "result_id", "deliverable_id", "problem_id", "scenario_id", "metric", "value", "unit",
        "comparison_or_baseline", "source_table", "source_figure", "source_script", "run_id",
        "validation_status", "frozen_at", "superseded_by", "notes",
    ],
    "claim_ledger.csv": [
        "claim_id", "location", "claim_text", "metric", "value", "unit", "scenario",
        "evidence_id", "evidence_type", "body_location", "status", "risk_note",
    ],
    "figure_evidence.csv": [
        "figure_id", "deliverable_id", "claim_id", "figure_path", "run_id", "caption", "post_figure_conclusion",
        "risk_note", "render_check_status", "human_visual_check", "visual_check_note", "validation_status",
    ],
    "consistency_audit.csv": [
        "audit_id", "claim_id", "artifact_a", "location_a", "artifact_b", "location_b",
        "mismatch_type", "expected", "observed", "severity", "minimum_fix", "owner", "status",
    ],
    "review_findings.csv": [
        "finding_id", "severity", "dimension", "score_risk", "artifact", "location",
        "issue", "impact", "minimum_fix", "owner", "status",
    ],
    "review_pass_items.csv": [
        "pass_item_id", "source_module", "claim_id", "file", "location", "value",
        "constraint_direction", "expected", "observed", "evidence_ref", "status", "notes",
    ],
}

MODEL_HANDOFF_TEMPLATE = """# 模型交接（model_handoff）

artifact_status: draft

## 当前锁定
- 题目/小问：待填写
- 对应交付物 ID：待填写
- 模型版本：v0

## 模型路线与选择理由
待填写：说明问题机制、主路线、baseline 及不选其他路线的原因。

## 变量、单位与定义
待填写：变量、参数、单位、定义域，并链接 `symbol_table.csv`。

## 目标与约束
待填写：目标函数、硬/软约束、边界条件和可行性判定。

## 输入与输出
待填写：真实数据路径、可信列、预处理/单位换算、结果表 schema、图表清单。

## PoC 与可复现运行
待填写：`poc_registry.csv` 的 passed 条目、正式 run_id、命令、seed/求解器设置。

## 验证与稳健性
待填写：量纲/边界/可行性检查、baseline、敏感性或风险分析、降级规则。

## 待解决缺口
待填写：任何不能由代码自行猜测的参数、单位、阈值、约束或输出格式。
"""

MODEL_REVIEW_TEMPLATE = """# 模型质量审查

artifact_status: draft

## 当前锁定
- 当前小问与交付物：待填写

## 路线质量
- 质量等级：blocked / usable-but-needs-review / national-first-candidate
- 任务契合：待填写
- baseline 与缺陷：待填写

## 数学对象
- 变量、单位、目标、约束、边界：待填写

## 结果与验证计划
- 结果表/图表：待填写
- PoC、检查、敏感性、复现：待填写

## 最小修复
待填写
"""

SUBMISSION_TEMPLATE = """# 提交与合规检查

artifact_status: draft
official_rule_source: unknown
rule_checked_at: unknown
anonymity_check: pending
reproducibility: pending
ai_disclosure_status: unknown

## 规则与格式
- 页数、命名、文件格式、附件要求：待核对官方规则。

## 匿名性
- 标题页、页眉页脚、PDF 元数据、文件名、代码注释、附录：待核对。

## 复现
- 核心运行命令、输入、环境、输出路径：待填写。

## AI 使用披露
- 仅在官方规则要求时填写最终披露位置；不要把披露文字塞入正文或图表。

## 未解决阻塞项
- 待填写。
"""

AI_LOG_TEMPLATE = """# AI 使用记录

仅当当前竞赛规则或用户要求追踪 AI 使用时填写。本记录是提交材料，不应自动写入论文正文、图表或代码注释。

- 官方规则来源与日期：待填写
- 工具/模型：待填写
- 使用阶段：待填写
- 采用内容：待填写
- 人工核验与修改：待填写
- 最终披露位置：待填写
"""


@dataclass
class Check:
    id: str
    level: str
    status: str  # pass / warn / fail
    message: str
    evidence: str = ""
    minimum_fix: str = ""


class ArtifactFreezeError(ValueError):
    """Raised when a run cannot be safely frozen without changing evidence."""


ARTIFACT_MANIFEST_NAME = "artifact_manifest.csv"
ARTIFACT_ROLES = {"entry_script", "input_file", "output_table", "output_figure"}
RUN_ARTIFACT_FIELDS = (
    ("entry_script", "entry_script", False),
    ("input_file", "input_files", True),
    ("output_table", "output_tables", True),
    ("output_figure", "output_figures", True),
)
NO_EXTERNAL_INPUT = "not_applicable"


def rel(project: Path, path: Path) -> str:
    try:
        return str(path.relative_to(project))
    except ValueError:
        return str(path)


def read_text(path: Path) -> str:
    try:
        return path.read_text(encoding="utf-8", errors="ignore")
    except Exception:
        return ""


def load_csv(path: Path) -> list[dict[str, str]]:
    if not path.exists():
        return []
    try:
        with path.open("r", encoding="utf-8-sig", newline="") as f:
            return [dict(row) for row in csv.DictReader(f)]
    except Exception:
        return []


def load_csv_strict(path: Path, headers: list[str]) -> list[dict[str, str]]:
    if not path.exists():
        return []
    try:
        with path.open("r", encoding="utf-8-sig", newline="") as handle:
            reader = csv.DictReader(handle)
            if reader.fieldnames != headers:
                raise ArtifactFreezeError(
                    f"Registry header mismatch for {path}: expected {headers}, got {reader.fieldnames}"
                )
            rows = [dict(row) for row in reader]
    except ArtifactFreezeError:
        raise
    except (OSError, UnicodeError, csv.Error) as exc:
        raise ArtifactFreezeError(f"Cannot read registry {path}: {exc}") from exc
    if any(None in row for row in rows):
        raise ArtifactFreezeError(f"Registry contains extra columns: {path}")
    return rows


def split_paths(value: str) -> list[str]:
    return [part.strip() for part in re.split(r"[;,\n]+", value or "") if part.strip()]


def safe_declared_file(project: Path, value: str) -> tuple[str, Path]:
    raw = clean(value)
    path = Path(raw)
    if not raw or path.is_absolute() or ".." in path.parts:
        raise ArtifactFreezeError(f"Artifact path must be a project-relative path without '..': {raw!r}")
    relative = path.as_posix()
    root = project.resolve()
    candidate = root / path
    try:
        resolved = candidate.resolve(strict=True)
        resolved.relative_to(root)
    except (OSError, RuntimeError, ValueError) as exc:
        raise ArtifactFreezeError(f"Artifact is missing or escapes the project: {relative}") from exc
    if not resolved.is_file():
        raise ArtifactFreezeError(f"Artifact is not a file: {relative}")
    return relative, candidate


def file_sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def file_fingerprint(path: Path) -> tuple[str, str]:
    try:
        before = path.stat()
        digest = file_sha256(path)
        after = path.stat()
    except OSError as exc:
        raise ArtifactFreezeError(f"Cannot read artifact {path}: {exc}") from exc
    identity_before = (before.st_dev, before.st_ino, before.st_size, before.st_mtime_ns)
    identity_after = (after.st_dev, after.st_ino, after.st_size, after.st_mtime_ns)
    if identity_before != identity_after:
        raise ArtifactFreezeError(f"Artifact changed while hashing: {path}")
    return digest, str(after.st_size)


def artifact_id(run_id: str, role: str, relative_path: str) -> str:
    identity = f"{run_id}\0{role}\0{relative_path}"
    return f"ART-{hashlib.sha256(identity.encode('utf-8')).hexdigest()[:12].upper()}"


def declared_run_artifacts(project: Path, run: dict[str, str]) -> list[tuple[str, str, Path]]:
    declared: list[tuple[str, str, Path]] = []
    seen: set[tuple[str, str]] = set()
    for role, field_name, multiple in RUN_ARTIFACT_FIELDS:
        raw_value = clean(run.get(field_name))
        if field_name == "input_files":
            if not raw_value:
                raise ArtifactFreezeError(
                    f"Completed run {clean(run.get('run_id'))!r} must list input_files or use {NO_EXTERNAL_INPUT!r}"
                )
            values = [] if raw_value.lower() == NO_EXTERNAL_INPUT else split_paths(raw_value)
        else:
            values = split_paths(raw_value) if multiple else [raw_value]
        if not multiple and not values[0]:
            raise ArtifactFreezeError(f"Completed run {clean(run.get('run_id'))!r} has no entry_script")
        for value in values:
            relative, path = safe_declared_file(project, value)
            identity = (role, relative)
            if identity not in seen:
                declared.append((role, relative, path))
                seen.add(identity)
    return declared


def has_reproduction_declaration(project: Path, run: dict[str, str]) -> bool:
    input_files = clean(run.get("input_files"))
    if not clean(run.get("command")) or not input_files:
        return False
    if input_files.lower() == NO_EXTERNAL_INPUT:
        return True
    try:
        return bool(split_paths(input_files)) and all(
            safe_declared_file(project, path) for path in split_paths(input_files)
        )
    except ArtifactFreezeError:
        return False


def validate_artifact_manifest_rows(rows: list[dict[str, str]]) -> None:
    artifact_ids: set[str] = set()
    identities: set[tuple[str, str, str]] = set()
    for row in rows:
        row_id = clean(row.get("artifact_id"))
        run_id = clean(row.get("run_id"))
        role = clean(row.get("role"))
        path = clean(row.get("path"))
        digest = clean(row.get("sha256")).lower()
        size = clean(row.get("bytes"))
        frozen_at = clean(row.get("frozen_at"))
        status = clean(row.get("status")).lower()
        if not row_id or not run_id or role not in ARTIFACT_ROLES or not path:
            raise ArtifactFreezeError("Artifact manifest contains a row with missing or invalid identity fields")
        lexical = Path(path)
        if lexical.is_absolute() or ".." in lexical.parts or lexical.as_posix() != path:
            raise ArtifactFreezeError(f"Artifact manifest contains an unsafe or non-normalized path: {path}")
        if row_id != artifact_id(run_id, role, path):
            raise ArtifactFreezeError(f"Artifact manifest has a non-deterministic artifact_id: {row_id}")
        if not re.fullmatch(r"[0-9a-f]{64}", digest) or not size.isdigit() or not frozen_at or status != "frozen":
            raise ArtifactFreezeError(f"Artifact manifest contains invalid hash, bytes, or status for {row_id}")
        identity = (run_id, role, path)
        if row_id in artifact_ids or identity in identities:
            raise ArtifactFreezeError(f"Artifact manifest contains a duplicate identity: {run_id}:{role}:{path}")
        artifact_ids.add(row_id)
        identities.add(identity)


def serialize_csv(headers: list[str], rows: list[dict[str, str]]) -> bytes:
    buffer = io.StringIO(newline="")
    writer = csv.DictWriter(buffer, fieldnames=headers)
    writer.writeheader()
    writer.writerows(rows)
    return b"\xef\xbb\xbf" + buffer.getvalue().encode("utf-8")


def atomic_write(path: Path, payload: bytes) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    descriptor, temporary_name = tempfile.mkstemp(prefix=f".{path.name}.", suffix=".tmp", dir=path.parent)
    temporary = Path(temporary_name)
    try:
        with os.fdopen(descriptor, "wb") as handle:
            handle.write(payload)
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temporary, path)
    finally:
        temporary.unlink(missing_ok=True)


@contextmanager
def artifact_manifest_lock(qc: Path) -> Iterator[None]:
    lock_path = qc / ".artifact_manifest.lock"
    lock_path.parent.mkdir(parents=True, exist_ok=True)
    try:
        with lock_path.open("a+b") as handle:
            fcntl.flock(handle.fileno(), fcntl.LOCK_EX)
            try:
                yield
            finally:
                fcntl.flock(handle.fileno(), fcntl.LOCK_UN)
    except OSError as exc:
        raise ArtifactFreezeError(f"Cannot lock artifact manifest {lock_path}: {exc}") from exc


def freeze_run_artifacts(project: Path, run_id: str) -> list[dict[str, str]]:
    project = project.expanduser().resolve()
    qc = project / QC_REL
    runs = load_csv_strict(qc / "run_record.csv", REGISTRY_HEADERS["run_record.csv"])
    matches = [row for row in runs if clean(row.get("run_id")) == clean(run_id)]
    if len(matches) != 1:
        raise ArtifactFreezeError(f"Expected exactly one run_record row for {run_id!r}, found {len(matches)}")
    run = matches[0]
    if clean(run.get("run_status")).lower() != "completed":
        raise ArtifactFreezeError(f"Run {run_id!r} is not completed")
    if not clean(run.get("command")):
        raise ArtifactFreezeError(f"Completed run {run_id!r} has no reproducible command")

    manifest_path = qc / ARTIFACT_MANIFEST_NAME
    headers = REGISTRY_HEADERS[ARTIFACT_MANIFEST_NAME]
    with artifact_manifest_lock(qc):
        declared = declared_run_artifacts(project, run)
        existing = load_csv_strict(manifest_path, headers)
        validate_artifact_manifest_rows(existing)
        previous = {
            (clean(row.get("role")), clean(row.get("path"))): row
            for row in existing
            if clean(row.get("run_id")) == clean(run_id)
        }
        frozen_at = datetime.now().astimezone().isoformat(timespec="seconds")
        frozen_rows: list[dict[str, str]] = []
        for role, relative, path in declared:
            digest, size = file_fingerprint(path)
            prior = previous.get((role, relative), {})
            unchanged = (
                clean(prior.get("sha256")).lower() == digest
                and clean(prior.get("bytes")) == size
                and clean(prior.get("status")).lower() == "frozen"
            )
            frozen_rows.append({
                "artifact_id": artifact_id(clean(run_id), role, relative),
                "run_id": clean(run_id),
                "role": role,
                "path": relative,
                "sha256": digest,
                "bytes": size,
                "frozen_at": clean(prior.get("frozen_at")) if unchanged else frozen_at,
                "status": "frozen",
                "notes": clean(prior.get("notes")),
            })
        combined = [row for row in existing if clean(row.get("run_id")) != clean(run_id)] + frozen_rows
        combined.sort(key=lambda row: (clean(row.get("run_id")), clean(row.get("role")), clean(row.get("path"))))
        validate_artifact_manifest_rows(combined)
        try:
            atomic_write(manifest_path, serialize_csv(headers, combined))
        except OSError as exc:
            raise ArtifactFreezeError(f"Cannot atomically update {manifest_path}: {exc}") from exc
        return [row for row in combined if clean(row.get("run_id")) == clean(run_id)]


def write_csv_template(path: Path, headers: list[str], force: bool) -> None:
    if path.exists() and not force:
        return
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8-sig", newline="") as f:
        csv.DictWriter(f, fieldnames=headers).writeheader()


def write_text_template(path: Path, content: str, force: bool) -> None:
    if path.exists() and not force:
        return
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")


def init_project(project: Path, force: bool = False) -> list[Path]:
    qc = project / QC_REL
    qc.mkdir(parents=True, exist_ok=True)
    for name, headers in REGISTRY_HEADERS.items():
        write_csv_template(qc / name, headers, force)
    write_text_template(qc / "model_handoff.md", MODEL_HANDOFF_TEMPLATE, force)
    write_text_template(qc / "model_quality_review.md", MODEL_REVIEW_TEMPLATE, force)
    write_text_template(qc / "submission_checklist.md", SUBMISSION_TEMPLATE, force)
    write_text_template(qc / "ai_usage_log.md", AI_LOG_TEMPLATE, force)
    hub_state = qc / "hub_state.json"
    if force or not hub_state.exists():
        hub_state.write_text(json.dumps({
            "artifact_status": "draft",
            "current_subquestion": "unknown",
            "deliverables_missing": [],
            "open_blockers": [],
            "allowed_next_action": "填写 problem_analysis.md 与 deliverable_matrix.csv",
            "paper_ready_claims": [],
            "compliance_status": "unknown",
            "updated_at": datetime.now().isoformat(timespec="seconds"),
        }, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return sorted(p for p in qc.iterdir() if p.is_file())


def non_template(text: str, minimum: int = 100) -> bool:
    stripped = "".join(text.split())
    placeholders = ("待填写", "待补充", "TODO", "unknown")
    return len(stripped) >= minimum and not any(token in text for token in placeholders)


def clean(value: Any) -> str:
    return str(value or "").strip()


def collect_registry_ids(
    rows: list[dict[str, str]], field: str, label: str,
) -> tuple[set[str], list[str]]:
    values = [clean(row.get(field)) for row in rows]
    issues: list[str] = []
    empty_count = sum(not value for value in values)
    if empty_count:
        issues.append(f"{label}:empty={empty_count}")
    seen: set[str] = set()
    duplicates: set[str] = set()
    for value in values:
        if not value:
            continue
        if value in seen:
            duplicates.add(value)
        seen.add(value)
    if duplicates:
        issues.append(f"{label}:duplicate={','.join(sorted(duplicates))}")
    return seen, issues


def is_resolved(value: str) -> bool:
    return clean(value).lower() in {"resolved", "fixed", "closed", "passed", "pass", "accepted"}


def path_exists_from_project(project: Path, value: str) -> bool:
    raw = clean(value)
    if not raw:
        return False
    root = project.resolve()
    candidate = Path(raw).expanduser()
    if not candidate.is_absolute():
        candidate = root / candidate
    try:
        resolved = candidate.resolve(strict=True)
        resolved.relative_to(root)
    except (OSError, RuntimeError, ValueError):
        return False
    return resolved.is_file()


def check_artifact_integrity(
    project: Path,
    runs: list[dict[str, str]],
    results: list[dict[str, str]],
    figures: list[dict[str, str]],
    completed_runs: set[str],
) -> tuple[bool, str, str]:
    paper_results = [
        row for row in results
        if clean(row.get("validation_status")).lower() == "paper_ready"
        and clean(row.get("run_id")) in completed_runs
    ]
    paper_figures = [
        row for row in figures
        if clean(row.get("validation_status")).lower() == "paper_ready"
        and clean(row.get("run_id")) in completed_runs
    ]
    supporting_run_ids = sorted({
        clean(row.get("run_id")) for row in paper_results + paper_figures if clean(row.get("run_id"))
    })
    if not supporting_run_ids:
        return False, "没有支撑 paper_ready 证据的 completed run 可供完整性核验", "supporting_runs=none"

    manifest_path = project / QC_REL / ARTIFACT_MANIFEST_NAME
    try:
        manifest = load_csv_strict(manifest_path, REGISTRY_HEADERS[ARTIFACT_MANIFEST_NAME])
        validate_artifact_manifest_rows(manifest)
    except ArtifactFreezeError as exc:
        return False, "产物冻结清单缺失或 schema 无效", str(exc)

    issues: list[str] = []
    verified_count = 0
    for run_id in supporting_run_ids:
        run_rows = [row for row in runs if clean(row.get("run_id")) == run_id]
        if len(run_rows) != 1:
            issues.append(f"{run_id}:run_record_count={len(run_rows)}")
            continue
        try:
            declared = declared_run_artifacts(project, run_rows[0])
        except ArtifactFreezeError as exc:
            issues.append(f"{run_id}:{exc}")
            continue

        expected = {(role, relative): path for role, relative, path in declared}
        frozen_rows = [row for row in manifest if clean(row.get("run_id")) == run_id]
        frozen = {(clean(row.get("role")), clean(row.get("path"))): row for row in frozen_rows}
        missing = sorted(set(expected) - set(frozen))
        extra = sorted(set(frozen) - set(expected))
        issues.extend(f"{run_id}:missing:{role}:{path}" for role, path in missing)
        issues.extend(f"{run_id}:undeclared:{role}:{path}" for role, path in extra)

        for identity in sorted(set(expected) & set(frozen)):
            role, relative = identity
            path = expected[identity]
            try:
                current_digest, current_size = file_fingerprint(path)
            except ArtifactFreezeError as exc:
                issues.append(f"{run_id}:unreadable:{relative}:{exc}")
                continue
            row = frozen[identity]
            if clean(row.get("sha256")).lower() != current_digest or clean(row.get("bytes")) != current_size:
                issues.append(f"{run_id}:drift:{role}:{relative}")
            else:
                verified_count += 1

        entry_paths = {path for role, path in expected if role == "entry_script"}
        input_paths = {path for role, path in expected if role == "input_file"}
        table_paths = {path for role, path in expected if role == "output_table"}
        figure_paths = {path for role, path in expected if role == "output_figure"}
        for row in paper_results:
            if clean(row.get("run_id")) != run_id:
                continue
            try:
                source_script, _ = safe_declared_file(project, clean(row.get("source_script")))
                source_table, _ = safe_declared_file(project, clean(row.get("source_table")))
            except ArtifactFreezeError as exc:
                issues.append(f"{run_id}:paper_result_reference:{exc}")
                continue
            if source_script not in entry_paths | input_paths:
                issues.append(f"{run_id}:source_script_not_frozen:{source_script}")
            if source_table not in table_paths:
                issues.append(f"{run_id}:source_table_not_output:{source_table}")
        for row in paper_figures:
            if clean(row.get("run_id")) != run_id:
                continue
            try:
                figure_path, _ = safe_declared_file(project, clean(row.get("figure_path")))
            except ArtifactFreezeError as exc:
                issues.append(f"{run_id}:paper_figure_reference:{exc}")
                continue
            if figure_path not in figure_paths:
                issues.append(f"{run_id}:figure_not_output:{figure_path}")

    if issues:
        return False, f"冻结产物存在 {len(issues)} 个缺失、漂移或 run 关联问题", "; ".join(issues)
    evidence = f"{rel(project, manifest_path)}; runs={','.join(supporting_run_ids)}; artifacts={verified_count}"
    return True, f"{len(supporting_run_ids)} 个 paper-ready 支撑 run 的 {verified_count} 个产物哈希一致", evidence


def evaluate(project: Path, phase: str) -> dict[str, Any]:
    qc = project / QC_REL
    checks: list[Check] = []

    def add(check_id: str, level: str, status: str, message: str, evidence: str = "", minimum_fix: str = "") -> None:
        checks.append(Check(check_id, level, status, message, evidence, minimum_fix))

    problem = project / "06_过程记录" / "problem_analysis.md"
    problem_ok = problem.exists() and non_template(read_text(problem), minimum=120)
    add(
        "problem_lock", "early", "pass" if problem_ok else "fail",
        "题目解析已形成可用锁定" if problem_ok else "题目解析缺失、过短或仍是空模板",
        rel(project, problem), "补齐每问目标、数据、约束、输出和题型路由。",
    )

    matrix_path = qc / "deliverable_matrix.csv"
    deliverables = load_csv(matrix_path)
    statuses = [clean(row.get("status")).lower() for row in deliverables]
    valid_deliverables = [row for row in deliverables if clean(row.get("deliverable_id")) and clean(row.get("required_output"))]
    if not valid_deliverables:
        add("deliverable_matrix", "early", "fail", "没有已定义的题目交付物", rel(project, matrix_path), "每个小问/输出至少填写一行。")
    elif any(status == "blocked" for status in statuses):
        add("deliverable_matrix", "early", "fail", "存在 blocked 交付物", rel(project, matrix_path), "解除阻塞或记录经规则/用户批准的 omission。")
    else:
        unsupported_omissions = [
            row for row in valid_deliverables
            if clean(row.get("status")).lower() == "accepted_omission"
            and not all(clean(row.get(field)) for field in ("approval_source", "omission_reason", "accepted_by"))
        ]
        if unsupported_omissions:
            add("deliverable_matrix", "early", "fail", "accepted_omission 缺少批准来源、原因或批准人", rel(project, matrix_path), "补齐 approval_source、omission_reason 和 accepted_by。")
        elif phase == "early":
            add("deliverable_matrix", "early", "pass", f"已锁定 {len(valid_deliverables)} 个交付物", rel(project, matrix_path))
        else:
            unfinished = [s for s in statuses if s not in {"provided", "accepted_omission"}]
            add(
                "deliverable_matrix", "model", "pass" if not unfinished else "fail",
                "所有交付物已提供或有正式豁免" if not unfinished else f"仍有 {len(unfinished)} 个交付物未完成",
                rel(project, matrix_path), "将所有 required/in_progress 行推进为 provided，或附理由标记 accepted_omission。",
            )

    handoff_path = qc / "model_handoff.md"
    handoff = read_text(handoff_path)
    handoff_sections = ("## 当前锁定", "## 模型路线与选择理由", "## 变量、单位与定义", "## 目标与约束", "## 输入与输出", "## 验证与稳健性")
    handoff_ok = all(section in handoff for section in handoff_sections) and non_template(handoff, minimum=240)
    if phase == "early":
        add("model_handoff", "early", "pass" if handoff_path.exists() else "warn", "模型交接模板存在" if handoff_path.exists() else "缺少 model_handoff.md", rel(project, handoff_path))
    else:
        add(
            "model_handoff", "model", "pass" if handoff_ok else "fail",
            "模型交接包含变量、单位、约束、输入输出与验证计划" if handoff_ok else "模型交接仍是模板或缺少不可猜测的建模事实",
            rel(project, handoff_path), "补齐路线理由、变量/单位、目标/约束、真实输入、结果 schema 和验证计划。",
        )

    if phase in {"model", "final"}:
        poc_path = qc / "poc_registry.csv"
        pocs = load_csv(poc_path)
        passed_pocs = [r for r in pocs if clean(r.get("status")).lower() == "passed"]
        real_pocs = [
            r for r in passed_pocs
            if clean(r.get("source_data")) and clean(r.get("source_slice"))
            and "synthetic" not in clean(r.get("source_data")).lower()
            and "mock" not in clean(r.get("source_data")).lower()
            and path_exists_from_project(project, clean(r.get("source_data")))
        ]
        add(
            "real_data_poc", "model", "pass" if real_pocs else "fail",
            f"存在 {len(real_pocs)} 个可追溯真实数据 PoC" if real_pocs else "缺少通过的、可追溯到本项目真实附件的数据 PoC",
            rel(project, poc_path), "记录 passed PoC 的 source_data、source_slice、命令、指标和值。",
        )

        verification_path = qc / "math_verification.csv"
        verifications = load_csv(verification_path)
        open_verification = [r for r in verifications if clean(r.get("status")).lower() in {"fail", "blocked", ""}]
        passed_verification = [r for r in verifications if clean(r.get("status")).lower() in {"passed", "pass", "non_applicable"}]
        add(
            "math_verification", "model", "pass" if passed_verification and not open_verification else "fail",
            "数学/约束/单位检查已记录且无开放硬问题" if passed_verification and not open_verification else "缺少数学检查，或仍有 fail/blocked 检查项",
            rel(project, verification_path), "至少记录量纲、边界或约束等具体检查，并修复所有硬失败。",
        )

        runs_path = qc / "run_record.csv"
        runs = load_csv(runs_path)
        completed_run_rows = [
            r for r in runs
            if clean(r.get("run_status")).lower() == "completed"
            and clean(r.get("run_id"))
            and has_reproduction_declaration(project, r)
            and path_exists_from_project(project, clean(r.get("entry_script")))
        ]
        completed_runs = {clean(r.get("run_id")) for r in completed_run_rows}
        add(
            "reproducible_run", "model", "pass" if completed_runs else "fail",
            f"存在 {len(completed_runs)} 个命令、输入声明和入口脚本完整的可复现运行" if completed_runs else "缺少 run_status=completed 且命令、输入声明、entry_script 完整的正式运行记录",
            rel(project, runs_path), f"记录命令、入口脚本、输入、参数、seed、输出和 run_id；无外部输入时填写 {NO_EXTERNAL_INPUT}。",
        )

        result_path = qc / "result_registry.csv"
        results = load_csv(result_path)
        allowed_result_status = {"computed", "checked", "paper_ready"}
        valid_results = [
            r for r in results
            if clean(r.get("validation_status")).lower() in allowed_result_status
            and clean(r.get("run_id")) in completed_runs
            and path_exists_from_project(project, clean(r.get("source_table")))
            and path_exists_from_project(project, clean(r.get("source_script")))
        ]
        add(
            "result_registry", "model", "pass" if valid_results else "fail",
            f"存在 {len(valid_results)} 个可追溯结果" if valid_results else "结果登记表缺少指向 completed run、源表和源脚本的有效结果",
            rel(project, result_path), "每个关键结果填 result_id、单位、存在的 source_table/source_script、run_id、validation_status。",
        )

    if phase == "final":
        results = load_csv(qc / "result_registry.csv")
        paper_result_rows = [
            r for r in results
            if clean(r.get("validation_status")).lower() == "paper_ready"
        ]
        ready_results = [
            r for r in paper_result_rows
            if clean(r.get("run_id")) in completed_runs
            and path_exists_from_project(project, clean(r.get("source_table")))
            and path_exists_from_project(project, clean(r.get("source_script")))
        ]
        _, result_identity_issues = collect_registry_ids(
            paper_result_rows, "result_id", "result_id",
        )
        if len(ready_results) != len(paper_result_rows):
            result_identity_issues.append(
                f"result_id:unqualified={len(paper_result_rows) - len(ready_results)}"
            )
        result_ids = {
            clean(row.get("result_id")) for row in ready_results if clean(row.get("result_id"))
        }
        figures_path = qc / "figure_evidence.csv"
        figures = load_csv(figures_path)
        paper_figure_rows = [
            r for r in figures
            if clean(r.get("validation_status")).lower() == "paper_ready"
        ]
        ready_figure_rows = [
            r for r in paper_figure_rows
            if clean(r.get("run_id")) in completed_runs
            and clean(r.get("caption"))
            and clean(r.get("post_figure_conclusion"))
            and (clean(r.get("render_check_status")).lower() == "passed" or clean(r.get("human_visual_check")).lower() == "passed")
            and path_exists_from_project(project, clean(r.get("figure_path")))
        ]
        _, figure_identity_issues = collect_registry_ids(
            paper_figure_rows, "figure_id", "figure_id",
        )
        if len(ready_figure_rows) != len(paper_figure_rows):
            figure_identity_issues.append(
                f"figure_id:unqualified={len(paper_figure_rows) - len(ready_figure_rows)}"
            )
        figure_ids = {
            clean(row.get("figure_id")) for row in ready_figure_rows if clean(row.get("figure_id"))
        }
        integrity_ok, integrity_message, integrity_evidence = check_artifact_integrity(
            project, runs, results, figures, completed_runs,
        )
        add(
            "artifact_integrity", "final", "pass" if integrity_ok else "fail",
            integrity_message, integrity_evidence,
            "对支撑论文证据的 completed run 执行 --freeze-run，并在代码、输入或输出变化后重新审核和冻结。",
        )
        claims_path = qc / "claim_ledger.csv"
        claims = load_csv(claims_path)
        paper_claims = [r for r in claims if clean(r.get("status")).lower() == "paper_ready"]
        _, claim_identity_issues = collect_registry_ids(paper_claims, "claim_id", "claim_id")
        claim_link_issues: list[str] = []
        for row in paper_claims:
            claim_id = clean(row.get("claim_id")) or "<empty>"
            evidence_id = clean(row.get("evidence_id"))
            evidence_type = clean(row.get("evidence_type")).lower()
            if not evidence_id:
                claim_link_issues.append(f"{claim_id}:empty_evidence_id")
            elif evidence_type == "result":
                if evidence_id not in result_ids:
                    claim_link_issues.append(f"{claim_id}:unknown_result:{evidence_id}")
            elif evidence_type == "figure":
                if evidence_id not in figure_ids:
                    claim_link_issues.append(f"{claim_id}:unknown_figure:{evidence_id}")
            else:
                claim_link_issues.append(f"{claim_id}:invalid_evidence_type:{evidence_type or '<empty>'}")
        claim_evidence_issues = (
            result_identity_issues + figure_identity_issues
            + claim_identity_issues + claim_link_issues
        )
        claim_evidence_ok = bool(paper_claims) and not claim_evidence_issues
        if claim_evidence_ok:
            claim_message = f"存在 {len(paper_claims)} 条具有唯一、类型化证据身份的 paper_ready 主张"
        elif not paper_claims:
            claim_message = "没有 paper_ready 论文主张"
        else:
            claim_message = f"论文级证据身份或主张映射存在 {len(claim_evidence_issues)} 个问题"
        claim_evidence_path = rel(project, claims_path)
        if claim_evidence_issues:
            claim_evidence_path += "; " + "; ".join(claim_evidence_issues)
        add(
            "paper_claim_evidence", "final", "pass" if claim_evidence_ok else "fail",
            claim_message, claim_evidence_path,
            "确保 paper_ready 的 result_id、figure_id、claim_id 非空且各自唯一，并按 evidence_type=result|figure 映射证据。",
        )
        provided_deliverable_ids = {
            clean(row.get("deliverable_id")) for row in valid_deliverables
            if clean(row.get("status")).lower() == "provided"
        }
        evidenced_deliverable_ids = {
            clean(row.get("deliverable_id")) for row in ready_results + ready_figure_rows
            if clean(row.get("deliverable_id"))
        }
        missing_deliverable_evidence = sorted(provided_deliverable_ids - evidenced_deliverable_ids)
        add(
            "deliverable_evidence_coverage", "final", "pass" if not missing_deliverable_evidence else "fail",
            "每个已提供交付物都有 paper_ready 结果或图表证据" if not missing_deliverable_evidence else f"缺少交付物证据映射：{', '.join(missing_deliverable_evidence)}",
            rel(project, qc / "deliverable_matrix.csv"), "为每个 provided deliverable 填 result_registry 或 figure_evidence 的 deliverable_id。",
        )
        add(
            "paper_figure_evidence", "final", "pass" if figure_ids else "warn",
            f"存在 {len(figure_ids)} 张经渲染或人工检查的 paper_ready 图" if figure_ids else "尚无 paper_ready 图表；若结论不依赖图表可说明原因，否则补图和可读性检查。",
            rel(project, figures_path), "为关键图表记录 run_id、caption、结论、视觉检查和 validation_status。",
        )

        review_path = qc / "review_findings.csv"
        findings = load_csv(review_path)
        open_high = [
            r for r in findings
            if clean(r.get("severity")).upper() in {"P0", "P1"} and not is_resolved(clean(r.get("status")))
        ]
        add(
            "judge_risk", "final", "pass" if not open_high else "fail",
            "不存在开放 P0/P1 评委风险" if not open_high else f"存在 {len(open_high)} 个未解决 P0/P1 风险",
            rel(project, review_path), "优先修复 P0/P1，再处理 presentation 类问题。",
        )

        consistency_path = qc / "consistency_audit.csv"
        consistency_rows = load_csv(consistency_path)
        open_consistency = [
            row for row in consistency_rows
            if (clean(row.get("severity")).upper() in {"P0", "P1"} and not is_resolved(clean(row.get("status"))))
            or clean(row.get("status")).lower() in {"fail", "blocked"}
        ]
        add(
            "consistency_audit", "final", "pass" if not open_consistency else "fail",
            "不存在开放的高风险一致性问题" if not open_consistency else f"存在 {len(open_consistency)} 个开放的一致性问题",
            rel(project, consistency_path), "修复值、单位、场景、baseline 或 validation_status 冲突，并记录 closed/resolved。",
        )

        pass_items_path = qc / "review_pass_items.csv"
        pass_items = [r for r in load_csv(pass_items_path) if clean(r.get("status")).lower() in {"passed", "pass"}]
        concrete_passes = [
            r for r in pass_items
            if all(clean(r.get(k)) for k in ("file", "location", "value", "constraint_direction", "observed"))
        ]
        add(
            "concrete_final_checks", "final", "pass" if len(concrete_passes) >= 5 else "warn",
            f"已记录 {len(concrete_passes)} 项具体通过检查" if len(concrete_passes) >= 5 else "最终审查不足 5 项可定位的通过证据",
            rel(project, pass_items_path), "记录文件、位置、值、预期关系、观测结果和证据来源。",
        )

        checklist_path = qc / "submission_checklist.md"
        checklist = read_text(checklist_path)
        compliance_ok = (
            "official_rule_source:" in checklist and "official_rule_source: unknown" not in checklist
            and "anonymity_check: passed" in checklist
            and "reproducibility: passed" in checklist
            and any(f"ai_disclosure_status: {value}" in checklist for value in ("passed", "not_required"))
        )
        add(
            "submission_compliance", "final", "pass" if compliance_ok else "fail",
            "官方规则、匿名、复现和 AI 披露状态均已明确" if compliance_ok else "提交合规清单仍缺官方规则、匿名、复现或 AI 披露状态",
            rel(project, checklist_path), "用当前官方规则来源填充 checklist，并完成匿名/复现/AI 披露核对。",
        )

    counts = {status: sum(c.status == status for c in checks) for status in ("pass", "warn", "fail")}
    if counts["fail"]:
        readiness = "blocked"
    elif counts["warn"]:
        readiness = "needs_review"
    else:
        readiness = {"early": "early_ready", "model": "model_ready", "final": "final_ready"}[phase]
    return {
        "schema_version": "1.0",
        "generated_at": datetime.now().isoformat(timespec="seconds"),
        "project": str(project),
        "phase": phase,
        "readiness": readiness,
        "counts": counts,
        "checks": [asdict(c) for c in checks],
        "quality_boundary": "final_ready is a documented contest-QC state, not an award guarantee.",
    }


def write_outputs(project: Path, summary: dict[str, Any]) -> tuple[Path, Path]:
    out_dir = project / QC_REL
    out_dir.mkdir(parents=True, exist_ok=True)
    json_path = out_dir / "contest_qc_gate.json"
    md_path = out_dir / "contest_qc_gate.md"
    json_path.write_text(json.dumps(summary, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    lines = ["# 竞赛质控门禁\n\n"]
    lines.append(f"- phase：`{summary['phase']}`\n")
    lines.append(f"- readiness：**{summary['readiness']}**\n")
    lines.append(f"- pass/warn/fail：{summary['counts']['pass']}/{summary['counts']['warn']}/{summary['counts']['fail']}\n")
    lines.append("- 口径：`final_ready` 只表示证据链与质控材料达到当前门禁要求，不保证获奖。\n\n")
    lines.append("| 层级 | 检查项 | 状态 | 说明 | 证据 | 最小修复 |\n|---|---|---|---|---|---|\n")
    icon = {"pass": "✅ pass", "warn": "⚠️ warn", "fail": "❌ fail"}
    for check in summary["checks"]:
        message = clean(check["message"]).replace("|", "/")
        evidence = clean(check["evidence"]).replace("|", "/")
        fix = clean(check["minimum_fix"]).replace("|", "/")
        lines.append(f"| {check['level']} | {check['id']} | {icon[check['status']]} | {message} | {evidence} | {fix} |\n")
    md_path.write_text("".join(lines), encoding="utf-8")
    return json_path, md_path


def main() -> int:
    parser = argparse.ArgumentParser(description="Initialize and run contest-quality evidence gates.")
    parser.add_argument("project", help="Modeling project directory")
    parser.add_argument("--init", action="store_true", help="Create non-destructive QC registries and templates")
    parser.add_argument("--force-templates", action="store_true", help="Overwrite only QC templates/headers; never delete project data")
    parser.add_argument("--freeze-run", metavar="RUN_ID", help="Freeze declared artifacts for one completed run without executing it")
    parser.add_argument("--phase", choices=("early", "model", "final"), default="final")
    parser.add_argument("--strict", action="store_true", help="Exit non-zero unless the selected phase is ready")
    args = parser.parse_args()
    project = Path(args.project).expanduser().resolve()
    if not project.exists():
        print(f"Project not found: {project}", file=sys.stderr)
        return 2
    if args.init:
        files = init_project(project, force=args.force_templates)
        print(f"QC templates: {len(files)} files under {project / QC_REL}")
    if args.freeze_run:
        try:
            frozen = freeze_run_artifacts(project, args.freeze_run)
        except ArtifactFreezeError as exc:
            print(f"Cannot freeze run {args.freeze_run}: {exc}", file=sys.stderr)
            return 2
        print(f"Frozen run {args.freeze_run}: {len(frozen)} artifacts -> {project / QC_REL / ARTIFACT_MANIFEST_NAME}")
    summary = evaluate(project, args.phase)
    json_path, md_path = write_outputs(project, summary)
    print(f"Contest QC ({args.phase}): {summary['readiness']}")
    print(f"Report: {md_path}")
    print(f"JSON: {json_path}")
    if args.strict and summary["readiness"] != f"{args.phase}_ready":
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
