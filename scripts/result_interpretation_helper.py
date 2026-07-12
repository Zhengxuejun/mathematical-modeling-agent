#!/usr/bin/env python3
"""Generate per-question result interpretation drafts for modeling reports.

Reads:
  - 06_过程记录/问题覆盖/problem_coverage.json, if available
  - 06_过程记录/problem_analysis.md
  - 03_结果表格/*.csv|*.json
  - 04_图表/*
  - 06_过程记录/一致性检查/auto_report_audit.json, if available
  - 06_过程记录/质量门禁/quality_gate_plus.json, if available

Writes:
  - 06_过程记录/结果解释/result_interpretation_draft.md
  - 06_过程记录/结果解释/result_interpretation_draft.json

This script does not invent conclusions. It surfaces available evidence and
creates conservative report-ready draft paragraphs with explicit caveats.
"""
from __future__ import annotations

import argparse
import csv
import json
import math
import re
import sys
from dataclasses import asdict, dataclass
from datetime import datetime
from pathlib import Path
from typing import Any

TABLE_EXTS = {".csv", ".json"}
FIGURE_EXTS = {".png", ".jpg", ".jpeg", ".svg", ".pdf"}
GENERIC_COLUMNS = {"id", "index", "序号", "编号", "name", "名称", "question", "问题", "qid"}
STOP_TOKENS = {
    "问题", "小问", "任务", "目标", "要求", "分析", "建立", "模型", "进行", "给出", "计算", "结果",
    "the", "and", "for", "with", "that", "this", "from", "using", "use", "test", "problem", "question",
}
DOMAIN_ALIASES = {
    "momentum": {"momentum", "serve", "adjusted", "point", "value", "ewma", "alpha", "动量", "发球", "优势"},
    "random": {"random", "randomness", "permutation", "pvalue", "p_value", "p-value", "run", "streak", "随机", "置换", "检验", "游程"},
    "swing": {"swing", "shift", "turning", "prediction", "predict", "auc", "accuracy", "classifier", "转换", "转折", "预测"},
    "sensitivity": {"sensitivity", "robust", "robustness", "alpha", "parameter", "scenario", "敏感", "鲁棒", "参数", "情景"},
    "recommend": {"recommend", "strategy", "coach", "policy", "suggestion", "建议", "策略", "教练", "方案"},
    "evaluate": {"evaluate", "evaluation", "score", "rank", "index", "indicator", "评价", "得分", "排序", "指标"},
    "forecast": {"forecast", "predict", "prediction", "trend", "future", "预测", "趋势", "未来"},
    "optimize": {"optimize", "optimization", "objective", "constraint", "cost", "route", "优化", "目标", "约束", "成本", "路径"},
}
GENERIC_RESULT_STEMS = {"modelresults", "mainmodelresults", "coremodelresults", "resultssummary", "summaryresults", "results", "modelsummary", "结果汇总", "模型结果"}


@dataclass
class TableSummary:
    path: str
    rows: int
    cols: int
    columns: list[str]
    numeric_columns: list[str]
    preview: list[dict[str, Any]]
    key_values: list[str]
    matched_questions: list[str]


@dataclass
class QuestionDraft:
    qid: str
    question: str
    status: str
    tables: list[str]
    figures: list[str]
    key_values: list[str]
    draft: str
    caveats: list[str]


def read_text_safe(path: Path) -> str:
    try:
        return path.read_text(encoding="utf-8", errors="ignore")
    except Exception:
        return ""


def load_json(path: Path) -> dict:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return {}


def files_under(project: Path, rel: str, exts: set[str]) -> list[Path]:
    root = project / rel
    if not root.exists():
        return []
    return sorted(p for p in root.rglob("*") if p.is_file() and not p.name.startswith("~$") and p.suffix.lower() in exts)


def normalize(text: str) -> str:
    return re.sub(r"\s+", "", text.lower())


def normalize_token(text: str) -> str:
    return re.sub(r"[^0-9a-zA-Z\u4e00-\u9fff]+", "", text).lower()


def text_tokens(text: str) -> set[str]:
    raw = re.findall(r"[\u4e00-\u9fff]{2,}|[A-Za-z][A-Za-z0-9_\-]{2,}|\d+(?:\.\d+)?", text)
    out: set[str] = set()
    for token in raw:
        t = normalize_token(token)
        if len(t) >= 2 and t not in STOP_TOKENS:
            out.add(t)
    return out


def expand_tokens(tokens: set[str]) -> set[str]:
    expanded = set(tokens)
    joined = " ".join(tokens)
    for trigger, aliases in DOMAIN_ALIASES.items():
        alias_norm = {normalize_token(a) for a in aliases if normalize_token(a)}
        if trigger in tokens or tokens.intersection(alias_norm) or any(a in joined for a in alias_norm if re.search(r"[\u4e00-\u9fff]", a)):
            expanded.update(alias_norm)
    return expanded


def extract_questions_fallback(problem_text: str) -> list[dict[str, Any]]:
    questions = []
    for raw in problem_text.splitlines():
        line = raw.strip()
        if not line:
            continue
        heading_match = re.match(r"^#{1,6}\s+(.+?)\s*$", line)
        if heading_match:
            line = heading_match.group(1).strip()
        m = re.match(r"^(?:[-*+•]\s*)?(?:问题|小问|任务|Question|Task|Problem|Q)\s*([一二三四五六七八九十\d]+)[：:、.\)）\s-]*(.+)$", line, flags=re.I)
        if not m:
            m = re.match(r"^(?:[-*+•]\s*)?(\d+)[、.\)）]\s*(.+)$", line)
        if m:
            qid = f"Q{m.group(1)}"
            text = m.group(2).strip() if len(m.groups()) >= 2 else line
            questions.append({"qid": qid, "text": text, "keywords": [qid, qid.replace("Q", "问题"), text]})
    return questions


def get_questions(project: Path) -> list[dict[str, Any]]:
    cov = load_json(project / "06_过程记录" / "问题覆盖" / "problem_coverage.json")
    coverage = cov.get("coverage") if isinstance(cov, dict) else None
    if isinstance(coverage, list) and coverage:
        return [
            {
                "qid": str(item.get("qid") or f"Q{i+1}"),
                "text": str(item.get("text") or ""),
                "keywords": list(item.get("keywords") or []),
                "coverage_status": str(item.get("status") or "unknown"),
                "warning": str(item.get("warning") or ""),
            }
            for i, item in enumerate(coverage)
        ]
    return extract_questions_fallback(read_text_safe(project / "06_过程记录" / "problem_analysis.md"))


def to_float(value: Any) -> float | None:
    if value is None:
        return None
    if isinstance(value, (int, float)) and not isinstance(value, bool):
        if math.isfinite(float(value)):
            return float(value)
        return None
    text = str(value).strip().replace(",", "")
    m = re.fullmatch(r"[-+]?\d+(?:\.\d+)?(?:[eE][-+]?\d+)?%?", text)
    if not m:
        return None
    try:
        if text.endswith("%"):
            return float(text[:-1]) / 100.0
        return float(text)
    except Exception:
        return None


def fmt_num(x: float) -> str:
    if abs(x) >= 1000:
        return f"{x:,.3g}"
    if abs(x) >= 10:
        return f"{x:.4g}"
    return f"{x:.4f}".rstrip("0").rstrip(".")


def read_csv_rows(path: Path, limit: int = 50) -> tuple[list[str], list[dict[str, Any]]]:
    with path.open("r", encoding="utf-8-sig", errors="ignore", newline="") as f:
        reader = csv.DictReader(f)
        rows = []
        for i, row in enumerate(reader):
            if i >= limit:
                break
            rows.append(dict(row))
        return list(reader.fieldnames or []), rows


def read_json_rows(path: Path, limit: int = 50) -> tuple[list[str], list[dict[str, Any]]]:
    obj = json.loads(path.read_text(encoding="utf-8"))
    if isinstance(obj, list):
        rows = [r for r in obj if isinstance(r, dict)][:limit]
    elif isinstance(obj, dict):
        # Prefer list-valued payloads if present; otherwise convert scalar dict.
        rows = []
        for v in obj.values():
            if isinstance(v, list) and v and isinstance(v[0], dict):
                rows = v[:limit]
                break
        if not rows:
            rows = [{k: v for k, v in obj.items() if not isinstance(v, (dict, list))}]
    else:
        rows = []
    cols = sorted({k for row in rows for k in row.keys()})
    return cols, rows


def row_question_text(row: dict[str, Any]) -> str:
    parts = []
    for k, v in row.items():
        if str(k).lower() in {"question", "qid", "问题", "小问", "task"}:
            parts.append(str(v))
    return " ".join(parts)


def row_text(row: dict[str, Any], max_items: int = 20) -> str:
    parts = []
    for i, (k, v) in enumerate(row.items()):
        if i >= max_items:
            break
        if v not in (None, ""):
            parts.append(f"{k} {v}")
    return " ".join(parts)


def question_tokens(q: dict[str, Any]) -> set[str]:
    base = " ".join([str(q.get("qid", "")), str(q.get("text", "")), " ".join(str(k) for k in q.get("keywords", [])[:12])])
    return expand_tokens(text_tokens(base))


def table_tokens(path: Path, rows: list[dict[str, Any]], columns: list[str]) -> set[str]:
    sample = "\n".join(row_text(r) for r in rows[:10])
    return expand_tokens(text_tokens(path.stem + " " + path.name + " " + " ".join(columns) + " " + sample))


def match_question(path: Path, rows: list[dict[str, Any]], questions: list[dict[str, Any]]) -> list[str]:
    hay = normalize(path.name + "\n" + "\n".join(row_question_text(r) for r in rows[:20]))
    all_columns = sorted({k for row in rows[:10] for k in row.keys()})
    hay_tokens = table_tokens(path, rows, all_columns)
    generic_stem = normalize_token(path.stem) in GENERIC_RESULT_STEMS
    matched = []
    for q in questions:
        qid = str(q.get("qid", ""))
        keys = [qid, qid.replace("Q", "问题"), qid.replace("Q", "小问")] + [str(k) for k in q.get("keywords", [])[:8]]
        q_tokens = question_tokens(q)
        overlap = q_tokens & hay_tokens
        if any(normalize(k) and normalize(k) in hay for k in keys) or len(overlap) >= 2 or (generic_stem and overlap):
            matched.append(qid)
    return matched


def summarize_rows(rows: list[dict[str, Any]], columns: list[str], max_values: int = 8) -> tuple[list[str], list[str]]:
    numeric_cols = []
    key_values = []
    for col in columns:
        vals = [to_float(row.get(col)) for row in rows]
        nums = [v for v in vals if v is not None]
        if nums:
            numeric_cols.append(col)
            if col.lower() not in GENERIC_COLUMNS:
                key_values.append(f"{col}={fmt_num(nums[-1])}")
                if len(nums) >= 2:
                    key_values.append(f"{col}_min={fmt_num(min(nums))}")
                    key_values.append(f"{col}_max={fmt_num(max(nums))}")
        if len(key_values) >= max_values:
            break
    if not key_values and rows:
        first = rows[0]
        for col in columns[:max_values]:
            value = first.get(col)
            if value not in (None, ""):
                key_values.append(f"{col}={value}")
    return numeric_cols, key_values[:max_values]


def summarize_table(project: Path, path: Path, questions: list[dict[str, Any]]) -> TableSummary | None:
    try:
        if path.suffix.lower() == ".csv":
            columns, rows = read_csv_rows(path)
        elif path.suffix.lower() == ".json":
            columns, rows = read_json_rows(path)
        else:
            return None
    except Exception:
        return None
    numeric_cols, key_values = summarize_rows(rows, columns)
    return TableSummary(
        path=str(path.relative_to(project)),
        rows=len(rows),
        cols=len(columns),
        columns=columns,
        numeric_columns=numeric_cols,
        preview=rows[:3],
        key_values=key_values,
        matched_questions=match_question(path, rows, questions),
    )


def match_assets_to_question(q: dict[str, Any], tables: list[TableSummary], figures: list[Path], project: Path) -> tuple[list[TableSummary], list[Path]]:
    qid = str(q.get("qid", ""))
    keys = [qid, qid.replace("Q", "问题"), qid.replace("Q", "小问")] + [str(k) for k in q.get("keywords", [])[:8]]
    norm_keys = [normalize(k) for k in keys if normalize(k)]
    q_tokens = question_tokens(q)
    matched_tables = []
    for t in tables:
        hay_text = t.path + "\n" + "\n".join(t.columns) + "\n" + "\n".join(t.key_values) + "\n" + json.dumps(t.preview, ensure_ascii=False)
        hay = normalize(hay_text)
        t_tokens = expand_tokens(text_tokens(hay_text))
        overlap = q_tokens & t_tokens
        generic_stem = normalize_token(Path(t.path).stem) in GENERIC_RESULT_STEMS
        if qid in t.matched_questions or any(k in hay for k in norm_keys) or len(overlap) >= 2 or (generic_stem and overlap):
            matched_tables.append(t)
    matched_figs = []
    for f in figures:
        hay_raw = str(f.relative_to(project))
        hay = normalize(hay_raw)
        f_tokens = expand_tokens(text_tokens(hay_raw))
        if any(k in hay for k in norm_keys) or len(q_tokens & f_tokens) >= 1:
            matched_figs.append(f)
    return matched_tables, matched_figs


def build_draft(q: dict[str, Any], tables: list[TableSummary], figures: list[Path], project: Path) -> QuestionDraft:
    qid = str(q.get("qid", ""))
    question = str(q.get("text", "")).strip()
    key_values: list[str] = []
    for t in tables:
        for kv in t.key_values:
            if kv not in key_values:
                key_values.append(kv)
    key_values = key_values[:10]
    table_paths = [t.path for t in tables]
    fig_paths = [str(f.relative_to(project)) for f in figures]
    caveats = []
    if not tables:
        caveats.append("未匹配到该小问的结果表，结论只能作为结构草稿，需补充数值证据。")
    if not figures:
        caveats.append("未匹配到该小问的图表，若报告需要可视化证据，应补充图表或说明无需图表。")
    if q.get("coverage_status") == "warn" or q.get("warning"):
        caveats.append(f"覆盖追踪提示：{q.get('warning') or q.get('coverage_status')}")

    evidence_sentence = ""
    if key_values:
        evidence_sentence = "关键结果包括：" + "；".join(key_values[:6]) + "。"
    elif tables:
        evidence_sentence = "已匹配到结果表，但未提取到稳定数值摘要，需人工核对表中关键指标。"
    else:
        evidence_sentence = "当前未匹配到可直接引用的结果表。"
    table_sentence = "、".join(table_paths) if table_paths else "未匹配"
    fig_sentence = "、".join(fig_paths) if fig_paths else "未匹配"
    draft = (
        f"【{qid}】针对“{question}”，现有结果证据来自表格：{table_sentence}；图表：{fig_sentence}。"
        f"{evidence_sentence}报告撰写时应先给出该问的直接结论，再解释模型/指标含义，最后说明敏感性或局限性。"
    )
    status = "pass" if tables else "warn"
    return QuestionDraft(qid=qid, question=question, status=status, tables=table_paths, figures=fig_paths, key_values=key_values, draft=draft, caveats=caveats)


def audit(project: Path) -> dict:
    questions = get_questions(project)
    table_paths = files_under(project, "03_结果表格", TABLE_EXTS)
    figures = files_under(project, "04_图表", FIGURE_EXTS)
    tables = [t for p in table_paths if (t := summarize_table(project, p, questions)) is not None]
    drafts: list[QuestionDraft] = []
    for q in questions:
        mt, mf = match_assets_to_question(q, tables, figures, project)
        drafts.append(build_draft(q, mt, mf, project))

    audit_json = load_json(project / "06_过程记录" / "一致性检查" / "auto_report_audit.json")
    quality_json = load_json(project / "06_过程记录" / "质量门禁" / "quality_gate_plus.json")
    coverage_json = load_json(project / "06_过程记录" / "问题覆盖" / "problem_coverage.json")
    warnings = []
    if audit_json.get("counts", {}).get("fail"):
        warnings.append("报告一致性审计存在 fail，解释草稿不能直接作为终稿结论。")
    if quality_json.get("counts", {}).get("fail"):
        warnings.append("增强质量门禁存在 fail，需先修复产物完整性。")
    if coverage_json.get("counts", {}).get("missing_questions"):
        warnings.append("问题覆盖追踪存在漏答小问，应先补报告覆盖。")

    counts = {
        "questions": len(drafts),
        "tables_read": len(tables),
        "figures": len(figures),
        "drafts_with_tables": sum(1 for d in drafts if d.tables),
        "drafts_without_tables": sum(1 for d in drafts if not d.tables),
        "warn": sum(1 for d in drafts if d.status == "warn") + len(warnings),
        "fail": 0 if drafts else 1,
    }
    return {
        "generated_at": datetime.now().isoformat(timespec="seconds"),
        "project": str(project),
        "counts": counts,
        "global_warnings": warnings,
        "table_summaries": [asdict(t) for t in tables],
        "drafts": [asdict(d) for d in drafts],
    }


def write_outputs(project: Path, summary: dict) -> tuple[Path, Path]:
    out_dir = project / "06_过程记录" / "结果解释"
    out_dir.mkdir(parents=True, exist_ok=True)
    json_path = out_dir / "result_interpretation_draft.json"
    md_path = out_dir / "result_interpretation_draft.md"
    json_path.write_text(json.dumps(summary, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    c = summary["counts"]
    lines: list[str] = []
    lines.append("# 模型结果解释草稿\n\n")
    lines.append(f"生成时间：{summary['generated_at']}\n\n")
    lines.append(f"项目：`{summary['project']}`\n\n")
    lines.append("## 汇总\n\n")
    lines.append(f"- 小问数：{c['questions']}\n- 已读取结果表：{c['tables_read']}\n- 图表数：{c['figures']}\n- 有表格证据草稿：{c['drafts_with_tables']}\n- 缺表格证据草稿：{c['drafts_without_tables']}\n- warn：{c['warn']}\n- fail：{c['fail']}\n\n")
    if summary.get("global_warnings"):
        lines.append("## 全局风险\n\n")
        for w in summary["global_warnings"]:
            lines.append(f"- ⚠️ {w}\n")
        lines.append("\n")
    lines.append("## 逐问解释草稿\n\n")
    for d in summary["drafts"]:
        lines.append(f"### {d['qid']}\n\n")
        lines.append(f"小问：{d['question']}\n\n")
        lines.append(d["draft"] + "\n\n")
        if d.get("key_values"):
            lines.append("可引用关键值：\n")
            for kv in d["key_values"]:
                lines.append(f"- `{kv}`\n")
            lines.append("\n")
        if d.get("caveats"):
            lines.append("风险提示：\n")
            for caveat in d["caveats"]:
                lines.append(f"- ⚠️ {caveat}\n")
            lines.append("\n")
    lines.append("## 结果表摘要\n\n| 文件 | 行 | 列 | 数值列 | 关键值 | 匹配小问 |\n|---|---:|---:|---|---|---|\n")
    for t in summary.get("table_summaries", []):
        numeric = ", ".join(t.get("numeric_columns", [])[:8]).replace("|", "\\|")
        kv = ", ".join(t.get("key_values", [])[:8]).replace("|", "\\|")
        mq = ", ".join(t.get("matched_questions", [])).replace("|", "\\|")
        lines.append(f"| `{t['path']}` | {t['rows']} | {t['cols']} | {numeric} | {kv} | {mq} |\n")
    md_path.write_text("".join(lines), encoding="utf-8")
    return json_path, md_path


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("project")
    parser.add_argument("--strict", action="store_true", help="Return non-zero if warnings exist")
    args = parser.parse_args()
    project = Path(args.project).expanduser().resolve()
    if not project.exists():
        print(f"Project not found: {project}", file=sys.stderr)
        return 2
    summary = audit(project)
    json_path, md_path = write_outputs(project, summary)
    c = summary["counts"]
    print(f"Result interpretation draft: {md_path}")
    print(f"Result interpretation json: {json_path}")
    print(f"Questions: {c['questions']}, drafts_without_tables={c['drafts_without_tables']}, fail={c['fail']}, warn={c['warn']}")
    if c["fail"]:
        return 1
    if args.strict and c["warn"]:
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
