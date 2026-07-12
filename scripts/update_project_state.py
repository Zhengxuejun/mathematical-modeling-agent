#!/usr/bin/env python3
"""Infer and update S0-S8 project state for mathematical modeling projects.

Creates/updates:
  06_过程记录/状态机/PROJECT_STATE.md
  project_meta.json

The script is evidence-based: a state is completed only when the corresponding
artifact exists. It never deletes files and only writes state/metadata files.
"""
from __future__ import annotations

import argparse
import json
import re
from dataclasses import asdict, dataclass
from datetime import datetime
from pathlib import Path

from submission_package_contract import validate_submission_package


@dataclass
class StateRule:
    code: str
    name: str
    evidence: list[str]
    description: str


@dataclass
class StateResult:
    code: str
    name: str
    complete: bool
    evidence_found: list[str]
    evidence_missing: list[str]
    description: str


STATE_RULES = [
    StateRule("S0", "材料获取", ["00_题目与资料/*", "01_原始数据/*"], "题面、附件或原始数据已放入项目"),
    StateRule("S1", "题目解析完成", ["06_过程记录/problem_analysis.md"], "每问目标、数据清单、输出要求、题型路由已记录"),
    StateRule("S2", "数据审计完成", ["03_结果表格/data_audit.csv"], "行列数、缺失值、字段、异常和单位风险已审计"),
    StateRule("S3", "基线模型完成", ["03_结果表格/*baseline*", "03_结果表格/*基线*"], "baseline 或 sanity check 已产出"),
    StateRule("S4", "核心模型完成", ["03_结果表格/*model_results*", "03_结果表格/*main_model*", "03_结果表格/*core_model*", "03_结果表格/*主模型*", "03_结果表格/*核心模型*"], "主模型结果已产出"),
    StateRule("S5", "敏感性/鲁棒性分析完成", ["03_结果表格/*sensitivity*", "03_结果表格/*robust*", "03_结果表格/*敏感*", "03_结果表格/*鲁棒*"], "关键参数扰动或替代模型验证已产出"),
    StateRule("S6", "报告初稿完成", ["05_报告定稿/*.md", "05_报告定稿/*.docx", "05_报告定稿/*.pdf", "05_报告定稿/*.tex"], "报告源文件或终稿文件已存在"),
    StateRule("S7", "一致性检查完成", ["06_过程记录/一致性检查/auto_report_audit.md", "06_过程记录/一致性检查/report_consistency_check.md"], "报告-结果一致性检查已完成"),
    StateRule("S8", "最终提交包完成", ["07_提交包/README_submit.md", "07_提交包/SHA256SUMS.txt", "07_提交包/submission_manifest.json"], "提交包、manifest 和校验文件已生成"),
]


def has_substantive_text(path: Path) -> bool:
    if not path.exists() or not path.is_file():
        return False
    try:
        text = path.read_text(encoding="utf-8", errors="ignore")
    except Exception:
        return path.stat().st_size > 0
    stripped = re.sub(r"[#\s`|:\-/\[\]（）()]+", "", text)
    placeholders = ["待补充", "todo", "TODO", "待完成"]
    if any(p in text for p in placeholders) and len(stripped) < 80:
        return False
    return len(stripped) >= 20


def match_pattern(project: Path, pattern: str) -> list[Path]:
    # pathlib glob handles Chinese paths and relative patterns.
    return sorted([p for p in project.glob(pattern) if p.exists() and p.is_file()])


def evidence_complete(project: Path, rule: StateRule) -> tuple[bool, list[str], list[str]]:
    if rule.code == "S8":
        validation = validate_submission_package(project / "07_提交包")
        found = [f"07_提交包/{path}" for path in validation.checked_files]
        return validation.valid, found, validation.reasons

    found: list[str] = []
    missing: list[str] = []
    # S0 can be satisfied by either problem/material or raw data.
    require_all = rule.code in {"S1", "S2", "S7", "S8"}
    for pat in rule.evidence:
        matches = match_pattern(project, pat)
        if rule.code in {"S1"}:
            matches = [p for p in matches if has_substantive_text(p)]
        if matches:
            found.extend(str(p.relative_to(project)) for p in matches[:20])
        else:
            missing.append(pat)
    if require_all:
        return len(missing) == 0, found, missing
    complete = len(found) > 0
    return complete, found, [] if complete else missing


def infer_states(project: Path) -> list[StateResult]:
    results: list[StateResult] = []
    for rule in STATE_RULES:
        complete, found, missing = evidence_complete(project, rule)
        results.append(StateResult(rule.code, rule.name, complete, found, missing, rule.description))
    return results


def highest_contiguous_state(results: list[StateResult]) -> str:
    highest = "S-1"
    for r in results:
        if r.complete:
            highest = r.code
        else:
            break
    return highest


def write_state_markdown(project: Path, results: list[StateResult], note: str = "") -> Path:
    out = project / "06_过程记录" / "状态机" / "PROJECT_STATE.md"
    out.parent.mkdir(parents=True, exist_ok=True)
    highest = highest_contiguous_state(results)
    lines: list[str] = []
    lines.append("# PROJECT_STATE\n\n")
    lines.append(f"更新时间：{datetime.now().isoformat(timespec='seconds')}\n\n")
    lines.append(f"当前连续完成状态：`{highest}`\n\n")
    if note:
        lines.append(f"备注：{note}\n\n")
    lines.append("| 状态 | 名称 | 完成? | 证据 | 缺失 |\n|---|---|---|---|---|\n")
    for r in results:
        done = "是" if r.complete else "否"
        found = "<br>".join(f"`{x}`" for x in r.evidence_found) if r.evidence_found else ""
        missing = "<br>".join(f"`{x}`" for x in r.evidence_missing) if r.evidence_missing else ""
        lines.append(f"| {r.code} | {r.name} | {done} | {found} | {missing} |\n")
    lines.append("\n## 状态说明\n\n")
    for r in results:
        lines.append(f"- **{r.code} {r.name}**：{r.description}\n")
    out.write_text("".join(lines), encoding="utf-8")
    return out


def update_meta(project: Path, results: list[StateResult]) -> Path:
    meta_path = project / "project_meta.json"
    if meta_path.exists():
        try:
            meta = json.loads(meta_path.read_text(encoding="utf-8"))
        except Exception:
            meta = {}
    else:
        meta = {}
    highest = highest_contiguous_state(results)
    meta.update({
        "updated_at": datetime.now().isoformat(timespec="seconds"),
        "highest_contiguous_state": highest,
        "state_summary": {r.code: r.complete for r in results},
        "skill": meta.get("skill", "mathematical-modeling-agent"),
    })
    meta_path.write_text(json.dumps(meta, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return meta_path


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("project")
    parser.add_argument("--note", default="")
    parser.add_argument("--check", action="store_true", help="Do not write files; return non-zero if no progress beyond S0")
    parser.add_argument("--strict", action="store_true", help="Return non-zero unless S8 is complete")
    args = parser.parse_args()

    project = Path(args.project).expanduser().resolve()
    if not project.exists():
        print(f"Project not found: {project}")
        return 2
    results = infer_states(project)
    highest = highest_contiguous_state(results)
    if not args.check:
        state_path = write_state_markdown(project, results, note=args.note)
        meta_path = update_meta(project, results)
        print(f"State file: {state_path}")
        print(f"Meta file: {meta_path}")
    print(f"Highest contiguous state: {highest}")
    incomplete = [r.code for r in results if not r.complete]
    if incomplete:
        print("Incomplete states:", ", ".join(incomplete))
    if args.strict and highest != "S8":
        return 1
    if args.check and highest in {"S-1", "S0"}:
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
