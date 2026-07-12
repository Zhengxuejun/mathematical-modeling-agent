#!/usr/bin/env python3
"""Track per-question coverage for mathematical modeling projects.

Reads the question/subtask list from:
  06_过程记录/problem_analysis.md

Then checks whether each extracted question appears to have evidence in:
  - final report text (05_报告定稿/*.md|*.tex|*.docx)
  - result tables (03_结果表格/*)
  - figures (04_图表/*)

Creates:
  06_过程记录/问题覆盖/problem_coverage.json
  06_过程记录/问题覆盖/problem_coverage.md

This script is a coverage gate: it helps detect omitted subquestions. It does
not prove that the mathematical answer is correct.
"""
from __future__ import annotations

import argparse
import json
import re
import sys
import zipfile
from dataclasses import asdict, dataclass
from datetime import datetime
from pathlib import Path
from xml.etree import ElementTree as ET

REPORT_EXTS = {".md", ".tex", ".docx"}
TABLE_EXTS = {".csv", ".json", ".xlsx", ".xls"}
FIGURE_EXTS = {".png", ".jpg", ".jpeg", ".svg", ".pdf"}
STOP_HEADINGS = ["数据清单", "输出要求", "题型路由", "方法", "模型", "假设", "符号", "验证"]
QUESTION_SECTION_HEADINGS = ["小问拆解", "问题拆解", "任务清单", "子任务", "问题列表", "Questions", "Tasks"]


@dataclass
class QuestionCoverage:
    qid: str
    text: str
    keywords: list[str]
    status: str
    report_hits: int
    table_hits: int
    figure_hits: int
    evidence: list[str]
    warning: str = ""


def read_text_safe(path: Path) -> str:
    try:
        return path.read_text(encoding="utf-8", errors="ignore")
    except Exception:
        return ""


def docx_text(path: Path) -> str:
    try:
        with zipfile.ZipFile(path) as zf:
            xml = zf.read("word/document.xml")
        root = ET.fromstring(xml)
        ns = {"w": "http://schemas.openxmlformats.org/wordprocessingml/2006/main"}
        return "\n".join(node.text or "" for node in root.findall(".//w:t", ns))
    except Exception:
        return ""


def report_text(path: Path) -> str:
    if path.suffix.lower() in {".md", ".tex"}:
        return read_text_safe(path)
    if path.suffix.lower() == ".docx":
        return docx_text(path)
    return ""


def files_under(project: Path, rel: str, exts: set[str]) -> list[Path]:
    root = project / rel
    if not root.exists():
        return []
    return sorted(p for p in root.rglob("*") if p.is_file() and not p.name.startswith("~$") and p.suffix.lower() in exts)


def normalize_text(text: str) -> str:
    return re.sub(r"\s+", "", text.lower())


def clean_question(line: str) -> str:
    line = line.strip()
    line = re.sub(r"^[-*+•]\s*", "", line)
    line = re.sub(r"^\|?\s*", "", line)
    line = re.sub(r"^(?:问题|小问|任务|Task|Question|Problem|Q)\s*([一二三四五六七八九十\d]+)[：:、.\)）\s-]*", r"问题\1：", line, flags=re.I)
    line = re.sub(r"^第\s*([一二三四五六七八九十\d]+)\s*(?:问|题)[：:、.\)）\s-]*", r"问题\1：", line)
    line = line.strip(" |\t")
    return line


def extract_section(text: str) -> str:
    lines = text.splitlines()
    start = None
    start_level = 99
    for i, line in enumerate(lines):
        m = re.match(r"^(#{1,6})\s*(.+?)\s*$", line.strip())
        if not m:
            continue
        title = m.group(2).strip()
        if any(h.lower() in title.lower() for h in QUESTION_SECTION_HEADINGS):
            start = i + 1
            start_level = len(m.group(1))
            break
    if start is None:
        return text
    end = len(lines)
    for j in range(start, len(lines)):
        m = re.match(r"^(#{1,6})\s*(.+?)\s*$", lines[j].strip())
        if not m:
            continue
        title = m.group(2).strip()
        if len(m.group(1)) <= start_level or any(h in title for h in STOP_HEADINGS):
            end = j
            break
    return "\n".join(lines[start:end])


def extract_questions(problem_text: str) -> list[str]:
    section = extract_section(problem_text)
    questions: list[str] = []
    for raw in section.splitlines():
        line = raw.strip()
        if not line:
            continue
        heading_match = re.match(r"^#{1,6}\s+(.+?)\s*$", line)
        if heading_match:
            line = heading_match.group(1).strip()
        if re.match(r"^\|\s*[-:]+", line):
            continue
        # Markdown table row: keep rows that look like a question/task item.
        if "|" in line and re.search(r"问题|小问|任务|Question|Task|Q\d+", line, flags=re.I):
            cells = [c.strip() for c in line.strip("|").split("|") if c.strip()]
            line = "：".join(cells[:2]) if len(cells) >= 2 else cells[0]
        item_like = re.match(
            r"^(?:[-*+•]\s*)?(?:问题|小问|任务|Task|Question|Problem|Q)\s*"
            r"[一二三四五六七八九十\d]+(?:[：:、.\)）\s-]|$)",
            line,
            flags=re.I,
        )
        numbered = re.match(r"^(?:[-*+•]\s*)?(?:\d+|[一二三四五六七八九十]+)[、.\)）]\s*\S+", line)
        if item_like or numbered:
            q = clean_question(line)
            if 4 <= len(re.sub(r"\s+", "", q)) <= 240:
                questions.append(q)
    # Deduplicate while preserving order.
    seen = set()
    unique = []
    for q in questions:
        key = normalize_text(q)
        if key not in seen:
            seen.add(key)
            unique.append(q)
    return unique


def make_qid(index: int, text: str) -> str:
    m = re.search(r"(?:问题|小问|任务|Question|Task|Problem|Q)\s*([一二三四五六七八九十\d]+)", text, flags=re.I)
    if m:
        return f"Q{m.group(1)}"
    return f"Q{index}"


def keywords_for_question(text: str, qid: str) -> list[str]:
    words: list[str] = []
    normalized_qid = qid.lower()
    words.extend([qid, normalized_qid, qid.replace("Q", "问题"), qid.replace("Q", "小问")])
    # Extract Chinese/English/digit chunks, dropping generic words.
    chunks = re.findall(r"[\u4e00-\u9fff]{2,}|[A-Za-z][A-Za-z0-9_\-]{2,}|\d+(?:\.\d+)?", text)
    stop = {"问题", "小问", "任务", "目标", "要求", "分析", "建立", "模型", "进行", "给出", "计算", "结果", "the", "and", "for", "with"}
    for c in chunks:
        if c in stop:
            continue
        if len(c) >= 2:
            words.append(c)
    # Keep high-signal first 12 unique tokens.
    out = []
    seen = set()
    for w in words:
        k = w.lower()
        if k not in seen:
            seen.add(k)
            out.append(w)
    return out[:12]


def hit_count(text: str, keywords: list[str]) -> int:
    norm = normalize_text(text)
    count = 0
    for kw in keywords:
        k = normalize_text(kw)
        if len(k) >= 2 and k in norm:
            count += 1
    return count


def file_text_for_search(path: Path) -> str:
    suffix = path.suffix.lower()
    if suffix in {".csv", ".json", ".svg"}:
        return read_text_safe(path)[:200_000]
    # For xlsx/images/pdf, filename is still useful evidence.
    return ""


def audit(project: Path, min_report_hits: int = 1, min_asset_hits: int = 0) -> dict:
    problem_path = project / "06_过程记录" / "problem_analysis.md"
    problem_text = read_text_safe(problem_path)
    questions = extract_questions(problem_text)

    reports = files_under(project, "05_报告定稿", REPORT_EXTS)
    report_combined = "\n".join(report_text(p) for p in reports)
    tables = files_under(project, "03_结果表格", TABLE_EXTS)
    figures = files_under(project, "04_图表", FIGURE_EXTS)

    table_search = "\n".join(str(p.relative_to(project)) + "\n" + file_text_for_search(p) for p in tables)
    figure_search = "\n".join(str(p.relative_to(project)) for p in figures)

    coverage: list[QuestionCoverage] = []
    for idx, q in enumerate(questions, start=1):
        qid = make_qid(idx, q)
        kws = keywords_for_question(q, qid)
        rh = hit_count(report_combined, kws)
        th = hit_count(table_search, kws)
        fh = hit_count(figure_search, kws)
        evidence = []
        if rh:
            evidence.append(f"report_hits={rh}")
        if th:
            evidence.append(f"table_hits={th}")
        if fh:
            evidence.append(f"figure_hits={fh}")
        status = "pass"
        warning = ""
        if rh < min_report_hits:
            status = "fail"
            warning = "报告未覆盖该小问关键词"
        elif (th + fh) < min_asset_hits:
            status = "warn"
            warning = "缺少结果表/图表侧证据"
        coverage.append(QuestionCoverage(qid=qid, text=q, keywords=kws, status=status, report_hits=rh, table_hits=th, figure_hits=fh, evidence=evidence, warning=warning))

    findings = []
    if not problem_path.exists():
        findings.append({"item": "problem_analysis_exists", "status": "fail", "detail": "problem_analysis.md 不存在", "evidence": str(problem_path.relative_to(project))})
    else:
        findings.append({"item": "problem_analysis_exists", "status": "pass", "detail": "problem_analysis.md 存在", "evidence": str(problem_path.relative_to(project))})
    if questions:
        findings.append({"item": "questions_extracted", "status": "pass", "detail": f"extracted={len(questions)}", "evidence": "; ".join(make_qid(i + 1, q) for i, q in enumerate(questions))})
    else:
        findings.append({"item": "questions_extracted", "status": "fail", "detail": "未从 problem_analysis.md 抽取到小问清单", "evidence": "请在『小问拆解』下用 问题1/问题2 或编号列表记录每一问"})
    findings.append({"item": "reports_readable", "status": "pass" if report_combined.strip() else "warn", "detail": f"reports={len(reports)}, text_chars={len(report_combined)}", "evidence": "; ".join(str(p.relative_to(project)) for p in reports[:10])})

    missing = [c for c in coverage if c.status == "fail"]
    weak = [c for c in coverage if c.status == "warn"]
    findings.append({"item": "all_questions_report_covered", "status": "fail" if missing else ("pass" if coverage else "fail"), "detail": f"missing={len(missing)}/{len(coverage)}", "evidence": "; ".join(c.qid for c in missing)})
    findings.append({"item": "question_asset_evidence", "status": "warn" if weak else "pass", "detail": f"weak={len(weak)}/{len(coverage)}", "evidence": "; ".join(c.qid for c in weak)})

    counts = {
        "questions": len(coverage),
        "pass": sum(1 for f in findings if f["status"] == "pass") + sum(1 for c in coverage if c.status == "pass"),
        "warn": sum(1 for f in findings if f["status"] == "warn") + sum(1 for c in coverage if c.status == "warn"),
        "fail": sum(1 for f in findings if f["status"] == "fail") + sum(1 for c in coverage if c.status == "fail"),
        "missing_questions": len(missing),
        "weak_asset_questions": len(weak),
    }
    return {
        "generated_at": datetime.now().isoformat(timespec="seconds"),
        "project": str(project),
        "problem_analysis": str(problem_path),
        "min_report_hits": min_report_hits,
        "min_asset_hits": min_asset_hits,
        "counts": counts,
        "findings": findings,
        "coverage": [asdict(c) for c in coverage],
    }


def write_outputs(project: Path, summary: dict) -> tuple[Path, Path]:
    out_dir = project / "06_过程记录" / "问题覆盖"
    out_dir.mkdir(parents=True, exist_ok=True)
    json_path = out_dir / "problem_coverage.json"
    md_path = out_dir / "problem_coverage.md"
    json_path.write_text(json.dumps(summary, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    lines: list[str] = []
    lines.append("# 问题小问覆盖追踪报告\n\n")
    lines.append(f"生成时间：{summary['generated_at']}\n\n")
    lines.append(f"项目：`{summary['project']}`\n\n")
    c = summary["counts"]
    lines.append("## 汇总\n\n")
    lines.append(f"- 小问数：{c['questions']}\n- pass: {c['pass']}\n- warn: {c['warn']}\n- fail: {c['fail']}\n- 未覆盖小问：{c['missing_questions']}\n- 侧证据较弱小问：{c['weak_asset_questions']}\n\n")
    lines.append("## 全局检查\n\n| 项目 | 状态 | 说明 | 证据 |\n|---|---|---|---|\n")
    for f in summary["findings"]:
        mark = {"pass": "✅", "warn": "⚠️", "fail": "❌"}.get(f["status"], f["status"])
        detail = str(f["detail"]).replace("|", "\\|")
        evidence = str(f.get("evidence", "")).replace("|", "\\|")
        lines.append(f"| {f['item']} | {mark} {f['status']} | {detail} | {evidence} |\n")
    lines.append("\n## 逐问覆盖\n\n| 小问 | 状态 | 报告命中 | 表格命中 | 图表命中 | 关键词 | 风险 |\n|---|---|---:|---:|---:|---|---|\n")
    for q in summary["coverage"]:
        mark = {"pass": "✅", "warn": "⚠️", "fail": "❌"}.get(q["status"], q["status"])
        kws = ", ".join(q.get("keywords", [])[:10]).replace("|", "\\|")
        text = q["text"].replace("|", "\\|")
        warning = q.get("warning", "").replace("|", "\\|")
        lines.append(f"| {q['qid']} {text} | {mark} {q['status']} | {q['report_hits']} | {q['table_hits']} | {q['figure_hits']} | {kws} | {warning} |\n")
    md_path.write_text("".join(lines), encoding="utf-8")
    return json_path, md_path


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("project")
    parser.add_argument("--strict", action="store_true", help="Return non-zero on warnings as well as failures")
    parser.add_argument("--min-report-hits", type=int, default=1, help="Minimum keyword hits in report text per question")
    parser.add_argument("--min-asset-hits", type=int, default=0, help="Minimum table+figure keyword hits per question; unmet gives warning")
    args = parser.parse_args()

    project = Path(args.project).expanduser().resolve()
    if not project.exists():
        print(f"Project not found: {project}", file=sys.stderr)
        return 2
    summary = audit(project, min_report_hits=args.min_report_hits, min_asset_hits=args.min_asset_hits)
    json_path, md_path = write_outputs(project, summary)
    c = summary["counts"]
    print(f"Problem coverage: {md_path}")
    print(f"Problem coverage json: {json_path}")
    print(f"Questions: {c['questions']}, missing={c['missing_questions']}, weak_assets={c['weak_asset_questions']}, fail={c['fail']}, warn={c['warn']}")
    if c["fail"]:
        return 1
    if args.strict and c["warn"]:
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
