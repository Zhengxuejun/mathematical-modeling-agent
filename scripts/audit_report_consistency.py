#!/usr/bin/env python3
"""Audit report-result consistency for mathematical modeling projects.

Creates:
  06_过程记录/一致性检查/auto_report_audit.json
  06_过程记录/一致性检查/auto_report_audit.md

Scope:
- Markdown/LaTeX: parse raw text.
- DOCX: parse document.xml with stdlib zip/xml.
- PDF: existence only; deep parsing intentionally avoided.
- Result tables: csv/json and xlsx when openpyxl is available.

This script checks consistency signals; it does not prove model correctness.
"""
from __future__ import annotations

import argparse
import csv
import json
import math
import re
import sys
import zipfile
from dataclasses import asdict, dataclass
from datetime import datetime
from pathlib import Path
from xml.etree import ElementTree as ET

REPORT_EXTS = {".md", ".tex", ".docx", ".pdf"}
FIGURE_EXTS = {".png", ".jpg", ".jpeg", ".pdf", ".svg"}
TABLE_EXTS = {".csv", ".json", ".xlsx", ".xls"}
UNITS = ["%", "kg", "吨", "t", "km", "公里", "m", "米", "周", "天", "小时", "元", "万元", "℃", "°C"]


@dataclass
class Finding:
    item: str
    status: str  # pass/warn/fail
    detail: str
    evidence: str = ""


def read_text(path: Path) -> str:
    return path.read_text(encoding="utf-8", errors="ignore")


def docx_text(path: Path) -> str:
    try:
        with zipfile.ZipFile(path) as zf:
            xml = zf.read("word/document.xml")
        root = ET.fromstring(xml)
        ns = {"w": "http://schemas.openxmlformats.org/wordprocessingml/2006/main"}
        texts = [node.text or "" for node in root.findall(".//w:t", ns)]
        return "\n".join(texts)
    except Exception as e:
        return f"[DOCX_PARSE_ERROR] {e!r}"


def get_report_text(path: Path) -> tuple[str, str]:
    suffix = path.suffix.lower()
    if suffix in {".md", ".tex"}:
        return read_text(path), "text"
    if suffix == ".docx":
        return docx_text(path), "docx"
    if suffix == ".pdf":
        return "", "pdf_unparsed"
    return "", "unsupported"


def normalize_stem(text: str) -> str:
    return re.sub(r"[^0-9a-zA-Z\u4e00-\u9fff]+", "", text).lower()


def normalize_ref_path(text: str) -> str:
    return text.split("#", 1)[0].split("?", 1)[0].strip().strip('"\'')


def is_raw_or_reference_table_ref(ref: str) -> bool:
    """Return True when a table-like filename is clearly not a result table.

    Modeling reports often mention raw attachments in the problem/data section
    (for example Wimbledon_featured_matches.csv). Those should not be checked
    against 03_结果表格 as result-table citations.
    """
    cleaned = normalize_ref_path(ref)
    lower = cleaned.lower()
    path_parts = [p for p in re.split(r"[/\\]+", lower) if p]
    raw_dirs = {"01_原始数据", "00_题目与资料", "raw", "data", "dataset", "datasets", "input", "inputs", "附件", "原始数据", "题目与资料"}
    if any(part in raw_dirs for part in path_parts):
        return True
    stem = Path(cleaned).stem.lower()
    raw_name_markers = (
        "raw", "input", "source", "original", "dataset", "data_dictionary", "dictionary",
        "featured_matches", "wimbledon_featured_matches", "附件", "原始", "题目", "数据字典"
    )
    result_markers = ("result", "results", "summary", "model", "baseline", "sensitivity", "prediction", "score", "rank", "结果", "汇总", "模型", "敏感性", "预测", "评价")
    return any(m in stem for m in raw_name_markers) and not any(m in stem for m in result_markers)


def find_files(root: Path, rel: str, exts: set[str]) -> list[Path]:
    d = root / rel
    if not d.exists():
        return []
    return sorted([p for p in d.rglob("*") if p.is_file() and p.suffix.lower() in exts])


def extract_asset_refs(text: str) -> tuple[set[str], set[str], set[str], dict[str, int]]:
    fig_refs: set[str] = set()
    table_refs: set[str] = set()
    raw_table_refs: set[str] = set()
    stats = {"fig_caption_refs": 0, "table_caption_refs": 0}
    # Markdown image paths.
    for m in re.findall(r"!\[[^\]]*\]\(([^)]+)\)", text):
        fig_refs.add(normalize_stem(Path(m.split("#", 1)[0].split("?", 1)[0]).stem))
    # LaTeX graphics.
    for m in re.findall(r"\\includegraphics(?:\[[^\]]*\])?\{([^}]+)\}", text):
        fig_refs.add(normalize_stem(Path(m).stem))
    # Explicit filenames.
    for m in re.findall(r"([\w\-\u4e00-\u9fff./]+\.(?:png|jpg|jpeg|svg|pdf))", text, flags=re.I):
        fig_refs.add(normalize_stem(Path(m).stem))
    for m in re.findall(r"([\w\-\u4e00-\u9fff./]+\.(?:csv|xlsx|xls|json))", text, flags=re.I):
        stem = normalize_stem(Path(normalize_ref_path(m)).stem)
        if is_raw_or_reference_table_ref(m):
            raw_table_refs.add(stem)
        else:
            table_refs.add(stem)
    stats["fig_caption_refs"] = len(re.findall(r"(?:图\s*\d+|Figure\s*\d+)", text, flags=re.I))
    stats["table_caption_refs"] = len(re.findall(r"(?:表\s*\d+|Table\s*\d+)", text, flags=re.I))
    return {x for x in fig_refs if x}, {x for x in table_refs if x}, {x for x in raw_table_refs if x}, stats


def extract_numbers(text: str) -> list[float]:
    nums: list[float] = []
    # Avoid digits embedded in words/filenames/paths such as fig1.png or 问题一.
    pattern = r"(?<![A-Za-z0-9_./\\-])[-+]?\d+(?:\.\d+)?\s*%?(?![A-Za-z0-9_./\\-])"
    for m in re.findall(pattern, text):
        raw = m.strip()
        pct = raw.endswith("%")
        raw = raw.rstrip("%").strip()
        try:
            val = float(raw)
            nums.append(val / 100 if pct else val)
        except ValueError:
            pass
    return nums


def extract_units(text: str) -> dict[str, int]:
    counts: dict[str, int] = {}
    for u in UNITS:
        if re.fullmatch(r"[A-Za-z]+", u):
            pattern = rf"(?<![A-Za-z]){re.escape(u)}(?![A-Za-z])"
        else:
            pattern = re.escape(u)
        n = len(re.findall(pattern, text, flags=re.I))
        if n:
            counts[u] = n
    return counts


def collect_table_numbers(path: Path) -> list[float]:
    suffix = path.suffix.lower()
    nums: list[float] = []
    try:
        if suffix == ".csv":
            with path.open("r", encoding="utf-8-sig", errors="ignore", newline="") as f:
                for row in csv.reader(f):
                    for cell in row:
                        nums.extend(extract_numbers(str(cell)))
        elif suffix == ".json":
            nums.extend(extract_numbers(path.read_text(encoding="utf-8", errors="ignore")))
        elif suffix in {".xlsx", ".xls"}:
            try:
                import openpyxl  # type: ignore
            except Exception:
                return nums
            wb = openpyxl.load_workbook(path, read_only=True, data_only=True)
            for ws in wb.worksheets:
                for row in ws.iter_rows(values_only=True):
                    for cell in row:
                        if isinstance(cell, (int, float)) and math.isfinite(float(cell)):
                            nums.append(float(cell))
                        elif cell is not None:
                            nums.extend(extract_numbers(str(cell)))
            wb.close()
    except Exception:
        return nums
    return nums


def approx_contains(value: float, candidates: list[float], rel_tol: float = 1e-3, abs_tol: float = 1e-6) -> bool:
    for c in candidates:
        if math.isfinite(value) and math.isfinite(c) and math.isclose(value, c, rel_tol=rel_tol, abs_tol=abs_tol):
            return True
        # Percent convention: report may write 85 while table stores 0.85 or vice versa.
        if abs(value) > 1 and math.isclose(value / 100, c, rel_tol=rel_tol, abs_tol=abs_tol):
            return True
        if abs(c) > 1 and math.isclose(value, c / 100, rel_tol=rel_tol, abs_tol=abs_tol):
            return True
    return False


def audit(project: Path, reports: list[Path], strict_numbers: bool = False) -> dict:
    figures = find_files(project, "04_图表", FIGURE_EXTS)
    tables = find_files(project, "03_结果表格", TABLE_EXTS)
    findings: list[Finding] = []

    if not reports:
        findings.append(Finding("report_exists", "fail", "未找到报告文件", "05_报告定稿/"))
    else:
        findings.append(Finding("report_exists", "pass", f"找到 {len(reports)} 个报告文件", "; ".join(str(p.relative_to(project)) for p in reports)))

    findings.append(Finding("figures_exist", "pass" if figures else "warn", f"找到 {len(figures)} 个图表文件", "; ".join(p.name for p in figures[:20])))
    findings.append(Finding("result_tables_exist", "pass" if tables else "warn", f"找到 {len(tables)} 个结果表文件", "; ".join(p.name for p in tables[:20])))

    all_text = []
    parsed_modes = []
    for r in reports:
        text, mode = get_report_text(r)
        parsed_modes.append(f"{r.name}:{mode}")
        if mode == "pdf_unparsed":
            findings.append(Finding("pdf_unparsed", "warn", f"PDF 不做深度解析，需要人工核对：{r.name}", str(r)))
        elif text.startswith("[DOCX_PARSE_ERROR]"):
            findings.append(Finding("docx_parse", "warn", text, str(r)))
        elif text:
            all_text.append(text)
    text = "\n".join(all_text)
    findings.append(Finding("report_text_parsed", "pass" if text else "warn", "; ".join(parsed_modes)))

    fig_refs, table_refs, raw_table_refs, stats = extract_asset_refs(text)
    fig_stems = {normalize_stem(p.stem): p for p in figures}
    table_stems = {normalize_stem(p.stem): p for p in tables}
    missing_figs = sorted([x for x in fig_refs if x not in fig_stems])
    missing_tables = sorted([x for x in table_refs if x not in table_stems])

    findings.append(Finding("figure_file_refs", "fail" if missing_figs else "pass", f"显式图文件引用 {len(fig_refs)} 个，缺失 {len(missing_figs)} 个", ", ".join(missing_figs[:20])))
    findings.append(Finding("table_file_refs", "fail" if missing_tables else "pass", f"显式结果表引用 {len(table_refs)} 个，缺失 {len(missing_tables)} 个", ", ".join(missing_tables[:20])))
    if raw_table_refs:
        findings.append(Finding("raw_table_refs_ignored", "pass", f"识别为原始数据/附件引用 {len(raw_table_refs)} 个，未按结果表缺失处理", ", ".join(sorted(raw_table_refs)[:20])))
    findings.append(Finding("caption_refs", "pass" if (stats["fig_caption_refs"] or stats["table_caption_refs"]) else "warn", f"图号引用 {stats['fig_caption_refs']}，表号引用 {stats['table_caption_refs']}"))

    # Numeric consistency: remove figure/table caption numbers before extracting values.
    text_for_numbers = re.sub(r"(?:图|表|Figure|Table)\s*\d+", " ", text, flags=re.I)
    report_numbers = [x for x in extract_numbers(text_for_numbers) if abs(x) < 10000]
    table_numbers: list[float] = []
    for t in tables:
        table_numbers.extend(collect_table_numbers(t))
    table_numbers = [x for x in table_numbers if abs(x) < 10000]
    # Deduplicate approximate display values to keep report useful.
    unique_report = []
    for x in report_numbers:
        if not approx_contains(x, unique_report, rel_tol=1e-9, abs_tol=1e-12):
            unique_report.append(x)
    unmatched = [x for x in unique_report if not approx_contains(x, table_numbers, rel_tol=1e-3, abs_tol=1e-6)]
    # Numeric matching is noisy; fail only in strict_numbers mode and when tables exist.
    if not table_numbers:
        findings.append(Finding("numeric_values_match_tables", "warn", "未抽取到结果表数字，无法核对摘要/正文数值"))
    elif unmatched:
        findings.append(Finding("numeric_values_match_tables", "fail" if strict_numbers else "warn", f"报告中 {len(unmatched)}/{len(unique_report)} 个唯一数字未在结果表近似匹配", ", ".join(f"{x:g}" for x in unmatched[:30])))
    else:
        findings.append(Finding("numeric_values_match_tables", "pass", f"报告中 {len(unique_report)} 个唯一数字均可在结果表近似匹配"))

    units = extract_units(text)
    if units:
        findings.append(Finding("units_detected", "pass", "检测到单位：" + ", ".join(f"{k}:{v}" for k, v in units.items())))
    else:
        findings.append(Finding("units_detected", "pass", "报告正文未检测到常见单位；若题目无量纲可忽略"))

    summary = {
        "generated_at": datetime.now().isoformat(timespec="seconds"),
        "project": str(project),
        "reports": [str(p) for p in reports],
        "figures": [str(p) for p in figures],
        "tables": [str(p) for p in tables],
        "counts": {
            "findings": len(findings),
            "fail": sum(1 for f in findings if f.status == "fail"),
            "warn": sum(1 for f in findings if f.status == "warn"),
            "pass": sum(1 for f in findings if f.status == "pass"),
        },
        "findings": [asdict(f) for f in findings],
    }
    return summary


def write_outputs(project: Path, summary: dict) -> tuple[Path, Path]:
    out_dir = project / "06_过程记录" / "一致性检查"
    out_dir.mkdir(parents=True, exist_ok=True)
    json_path = out_dir / "auto_report_audit.json"
    md_path = out_dir / "auto_report_audit.md"
    json_path.write_text(json.dumps(summary, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    lines = ["# 自动报告一致性审计\n\n"]
    lines.append(f"生成时间：{summary['generated_at']}\n\n")
    lines.append(f"项目：`{summary['project']}`\n\n")
    c = summary["counts"]
    lines.append(f"## 汇总\n\n- pass: {c['pass']}\n- warn: {c['warn']}\n- fail: {c['fail']}\n\n")
    lines.append("## 明细\n\n| 项目 | 状态 | 说明 | 证据 |\n|---|---|---|---|\n")
    for f in summary["findings"]:
        mark = {"pass": "✅", "warn": "⚠️", "fail": "❌"}.get(f["status"], f["status"])
        detail = str(f["detail"]).replace("|", "\\|")
        evidence = str(f.get("evidence", "")).replace("|", "\\|")
        lines.append(f"| {f['item']} | {mark} {f['status']} | {detail} | {evidence} |\n")
    md_path.write_text("".join(lines), encoding="utf-8")
    return json_path, md_path


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("project")
    parser.add_argument("--report", action="append", default=None, help="Report path relative to project or absolute; can repeat")
    parser.add_argument("--strict", action="store_true", help="Return non-zero on warnings as well as failures")
    parser.add_argument("--strict-numbers", action="store_true", help="Treat unmatched report numbers as failures instead of warnings")
    args = parser.parse_args()

    project = Path(args.project).expanduser().resolve()
    if not project.exists():
        print(f"Project not found: {project}", file=sys.stderr)
        return 2
    if args.report:
        reports = []
        for item in args.report:
            p = Path(item).expanduser()
            if not p.is_absolute():
                p = project / p
            if p.exists() and p.is_file():
                reports.append(p)
            else:
                # keep missing report as a failure through empty reports + explicit message
                print(f"Report not found: {p}", file=sys.stderr)
        if not reports:
            reports = []
    else:
        report_dir = project / "05_报告定稿"
        reports = sorted([p for p in report_dir.rglob("*") if p.is_file() and p.suffix.lower() in REPORT_EXTS]) if report_dir.exists() else []

    summary = audit(project, reports, strict_numbers=args.strict_numbers)
    json_path, md_path = write_outputs(project, summary)
    c = summary["counts"]
    print(f"Audit report: {md_path}")
    print(f"Audit json: {json_path}")
    print(f"Findings: {c['findings']} total, {c['fail']} fail, {c['warn']} warn")
    if c["fail"]:
        return 1
    if args.strict and c["warn"]:
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
