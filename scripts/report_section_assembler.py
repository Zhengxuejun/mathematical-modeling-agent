#!/usr/bin/env python3
"""Assemble an evidence-first editable Markdown report skeleton.

Reads:
  - 06_过程记录/problem_analysis.md
  - 06_过程记录/结果解释/result_interpretation_draft.json, if available
  - 06_过程记录/问题覆盖/problem_coverage.json, if available
  - 06_过程记录/一致性检查/auto_report_audit.json, if available
  - 06_过程记录/质量门禁/quality_gate_plus.json, if available
  - 03_结果表格/* and 04_图表/* as fallback evidence inventory

Writes:
  - 05_报告定稿/report_draft.md
  - 06_过程记录/报告拼装/report_section_assembly.json
  - 06_过程记录/报告拼装/report_section_assembly.md

This script does not claim final conclusions. It creates an editable skeleton that
forces each question to contain: direct answer placeholder, model/method,
evidence tables, figure interpretation, and limitations/sensitivity notes.
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from dataclasses import asdict, dataclass
from datetime import datetime
from pathlib import Path
from typing import Any

TABLE_EXTS = {".csv", ".json", ".xlsx", ".xls"}
FIGURE_EXTS = {".png", ".jpg", ".jpeg", ".svg", ".pdf"}
RAW_DATA_EXTS = TABLE_EXTS | {".txt", ".tsv", ".dat", ".zip"}
RAW_DATA_DIRS = ("01_原始数据", "00_题目与资料")
RAW_DIR_MARKERS = {"01_原始数据", "00_题目与资料", "raw", "data", "dataset", "datasets", "input", "inputs", "附件", "原始数据", "题目与资料"}
RAW_DIR_MARKERS_NORM = {re.sub(r"[^0-9a-zA-Z\u4e00-\u9fff]+", "", x).lower() for x in RAW_DIR_MARKERS}
RAW_NAME_MARKERS = (
    "raw", "input", "source", "original", "dataset", "data_dictionary", "dictionary",
    "featured_matches", "wimbledon_featured_matches", "附件", "原始", "题目", "数据字典",
)
RESULT_NAME_MARKERS = ("result", "results", "summary", "model", "baseline", "sensitivity", "prediction", "score", "rank", "结果", "汇总", "模型", "敏感性", "预测", "评价")


@dataclass
class Section:
    qid: str
    question: str
    tables: list[str]
    figures: list[str]
    key_values: list[str]
    caveats: list[str]
    completeness: str
    markdown: str


def read_text_safe(path: Path) -> str:
    try:
        return path.read_text(encoding="utf-8", errors="ignore")
    except Exception:
        return ""


def load_json(path: Path) -> dict[str, Any]:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return {}


def rel(project: Path, path: Path) -> str:
    try:
        return str(path.relative_to(project))
    except Exception:
        return str(path)


def normalize(text: str) -> str:
    return re.sub(r"\s+", "", text.lower())

def normalize_ref_path(text: str) -> str:
    return text.split("#", 1)[0].split("?", 1)[0].strip().strip('"\'')


def is_raw_or_reference_table_ref(ref: str) -> bool:
    """Return True when a table-like reference is raw data/material, not result evidence."""
    cleaned = normalize_ref_path(ref)
    lower = cleaned.lower()
    path_parts = [p for p in re.split(r"[/\\]+", lower) if p]
    norm_parts = [re.sub(r"[^0-9a-zA-Z\u4e00-\u9fff]+", "", p).lower() for p in path_parts]
    if any(part in RAW_DIR_MARKERS_NORM for part in norm_parts):
        return True
    stem = Path(cleaned).stem.lower()
    return any(m in stem for m in RAW_NAME_MARKERS) and not any(m in stem for m in RESULT_NAME_MARKERS)


def list_raw_data_files(project: Path) -> list[str]:
    files: list[str] = []
    for subdir in RAW_DATA_DIRS:
        root = project / subdir
        if not root.exists():
            continue
        files.extend(
            rel(project, p)
            for p in root.rglob("*")
            if p.is_file() and not p.name.startswith("~$") and p.suffix.lower() in RAW_DATA_EXTS
        )
    return sorted(set(files))


def extract_raw_data_refs(problem_text: str, raw_files: list[str]) -> list[str]:
    """Extract raw-data filenames mentioned in problem_analysis and resolve them to project paths when possible."""
    by_name = {Path(p).name.lower(): p for p in raw_files}
    by_stem = {Path(p).stem.lower(): p for p in raw_files}
    refs: list[str] = []
    for m in re.findall(r"([\w\-\u4e00-\u9fff./]+\.(?:csv|xlsx|xls|json|txt|tsv|dat|zip))", problem_text, flags=re.I):
        cleaned = normalize_ref_path(m)
        suffix = Path(cleaned).suffix.lower()
        if suffix not in RAW_DATA_EXTS:
            continue
        resolved = by_name.get(Path(cleaned).name.lower()) or by_stem.get(Path(cleaned).stem.lower())
        if resolved:
            refs.append(resolved)
        elif is_raw_or_reference_table_ref(cleaned):
            refs.append(cleaned)
    return sorted(dict.fromkeys(refs))


def annotate_raw_refs(text: str, raw_refs: list[str]) -> str:
    """Mark raw data references so generated report text does not look like result-table citations."""
    if not raw_refs:
        return text
    replacements: dict[str, str] = {}
    for ref in raw_refs:
        name = Path(ref).name
        # Prefer project-relative raw-data path when a matching raw file is known.
        display = ref if any(ref.startswith(d + "/") for d in RAW_DATA_DIRS) else name
        replacements[name] = f"`{display}`（原始数据引用，非结果表）"
        replacements[ref] = f"`{display}`（原始数据引用，非结果表）"
    out = text
    for src in sorted(replacements, key=len, reverse=True):
        out = re.sub(rf"(?<![`\w./-]){re.escape(src)}(?![`\w./-])", replacements[src], out)
    return out


def raw_data_reference_block(raw_refs: list[str]) -> str:
    if not raw_refs:
        return "- 暂未从 `problem_analysis.md` 自动识别原始数据文件；若题目有附件，请在此补充文件名、字段含义和用途。"
    return "\n".join(f"- `{ref}`：原始数据引用，非 `03_结果表格/` 的结果证据表。" for ref in raw_refs)



def list_files(project: Path, subdir: str, exts: set[str]) -> list[str]:
    root = project / subdir
    if not root.exists():
        return []
    return sorted(rel(project, p) for p in root.rglob("*") if p.is_file() and not p.name.startswith("~$") and p.suffix.lower() in exts)


def extract_questions_fallback(problem_text: str) -> list[dict[str, Any]]:
    questions: list[dict[str, Any]] = []
    for raw in problem_text.splitlines():
        line = raw.strip()
        if not line or line.startswith("#"):
            continue
        m = re.match(r"^(?:[-*+•]\s*)?(?:问题|小问|任务|Question|Task|Q)\s*([一二三四五六七八九十\d]+)[：:、.\)）\s-]*(.+)$", line, flags=re.I)
        if not m:
            m = re.match(r"^(?:[-*+•]\s*)?(\d+)[、.\)）]\s*(.+)$", line)
        if m:
            token = m.group(1)
            questions.append({"qid": f"Q{token}", "text": m.group(2).strip(), "keywords": [f"Q{token}", f"问题{token}", m.group(2).strip()]})
    return questions


def get_questions(project: Path) -> list[dict[str, Any]]:
    interp = load_json(project / "06_过程记录" / "结果解释" / "result_interpretation_draft.json")
    drafts = interp.get("drafts") if isinstance(interp, dict) else None
    if isinstance(drafts, list) and drafts:
        return [
            {
                "qid": str(d.get("qid") or f"Q{i+1}"),
                "text": str(d.get("question") or ""),
                "tables": list(d.get("tables") or []),
                "figures": list(d.get("figures") or []),
                "key_values": list(d.get("key_values") or []),
                "caveats": list(d.get("caveats") or []),
            }
            for i, d in enumerate(drafts)
        ]

    cov = load_json(project / "06_过程记录" / "问题覆盖" / "problem_coverage.json")
    coverage = cov.get("coverage") if isinstance(cov, dict) else None
    if isinstance(coverage, list) and coverage:
        return [
            {
                "qid": str(c.get("qid") or f"Q{i+1}"),
                "text": str(c.get("text") or ""),
                "keywords": list(c.get("keywords") or []),
                "tables": list(c.get("table_hits") or []),
                "figures": list(c.get("figure_hits") or []),
                "key_values": [],
                "caveats": [str(c.get("warning"))] if c.get("warning") else [],
            }
            for i, c in enumerate(coverage)
        ]

    return extract_questions_fallback(read_text_safe(project / "06_过程记录" / "problem_analysis.md"))


def match_fallback_assets(q: dict[str, Any], tables: list[str], figures: list[str]) -> tuple[list[str], list[str]]:
    qid = str(q.get("qid") or "")
    keys = [qid, qid.replace("Q", "问题"), qid.replace("Q", "小问")] + [str(k) for k in q.get("keywords", [])]
    norm_keys = [normalize(k) for k in keys if normalize(k)]
    mt = [p for p in tables if any(k in normalize(p) for k in norm_keys)]
    mf = [p for p in figures if any(k in normalize(p) for k in norm_keys)]
    return mt, mf


def bullet_list(items: list[str], empty: str) -> str:
    if not items:
        return f"- {empty}\n"
    return "".join(f"- `{item}`\n" for item in items)


def build_section(project: Path, q: dict[str, Any], all_tables: list[str], all_figures: list[str]) -> Section:
    qid = str(q.get("qid") or "Q?")
    question = str(q.get("text") or q.get("question") or "").strip()
    tables = list(q.get("tables") or [])
    figures = list(q.get("figures") or [])
    if not tables or not figures:
        mt, mf = match_fallback_assets(q, all_tables, all_figures)
        tables = tables or mt
        figures = figures or mf
    key_values = list(q.get("key_values") or [])[:12]
    caveats = [str(x) for x in q.get("caveats", []) if str(x).strip()]
    if not tables:
        caveats.append("本小问未匹配到结果表；报告中必须补充表格证据或说明该问不需要数值表。")
    if not figures:
        caveats.append("本小问未匹配到图表；若该问需要可视化支撑，应补图或说明无需图表。")
    completeness = "ready" if tables and figures else ("partial" if tables or figures else "weak")

    kv_text = "\n".join(f"- `{kv}`" for kv in key_values) if key_values else "- 暂无自动提取关键值；请从结果表中补入核心指标。"
    caveat_text = "\n".join(f"- ⚠️ {c}" for c in caveats) if caveats else "- 暂无自动风险提示；仍需人工检查模型假设、单位和常识一致性。"

    md = f"""## {qid} {question}

### 1. 直接结论

> 待编辑：用 1–3 句话直接回答本小问，不先铺模型背景。结论必须来自下方证据表/图表。

### 2. 模型与方法

> 待编辑：说明本问使用的模型、关键变量、目标函数/评价指标/预测指标，以及选择该方法的理由。

### 3. 证据表

{bullet_list(tables, "未匹配到结果表，请补充 `03_结果表格/q*_*.csv` 或在正文说明无需表格。")}

可引用关键值：
{kv_text}

### 4. 图表解释

{bullet_list(figures, "未匹配到图表，请补充 `04_图表/q*_*.png` 或说明无需图表。")}

> 待编辑：解释图表展示的排序、趋势、拐点、异常值或对比关系；不要只写“如图所示”。

### 5. 敏感性、鲁棒性与局限性

{caveat_text}

> 待编辑：说明关键参数扰动、替代模型、数据限制、适用边界，以及结论在什么条件下可能变化。
"""
    return Section(qid=qid, question=question, tables=tables, figures=figures, key_values=key_values, caveats=caveats, completeness=completeness, markdown=md)


def extract_problem_overview(problem_text: str) -> str:
    lines = [ln.strip() for ln in problem_text.splitlines()]
    useful = []
    for ln in lines:
        if not ln or ln.startswith("#"):
            continue
        useful.append(ln)
        if len("".join(useful)) > 500:
            break
    return "\n".join(useful[:8])


def build_report(project: Path, sections: list[Section], title: str) -> str:
    problem_text = read_text_safe(project / "06_过程记录" / "problem_analysis.md")
    raw_refs = extract_raw_data_refs(problem_text, list_raw_data_files(project))
    overview = extract_problem_overview(problem_text) or "待补充：概括背景、研究对象、数据来源和各小问目标。"
    overview = annotate_raw_refs(overview, raw_refs)
    raw_block = raw_data_reference_block(raw_refs)
    now = datetime.now().isoformat(timespec="seconds")
    section_text = "\n".join(s.markdown for s in sections)
    return f"""# {title}

> 自动生成时间：{now}  
> 生成器：`report_section_assembler.py`  
> 注意：这是证据优先的可编辑报告骨架，不是终稿。所有“待编辑”段落必须结合真实模型、代码和结果人工复核。

## 摘要

待编辑：按“问题—方法—核心结果—结论”写摘要。核心数值必须来自 `03_结果表格/`，不要编造。

## 一、问题重述

{overview}

## 二、模型假设

1. 待编辑：列出与数据、系统边界、变量独立性、时间/空间范围有关的假设。
2. 待编辑：说明每条假设的合理性和可能影响。
3. 待编辑：如果存在简化或忽略项，必须明确写出。

## 三、符号说明

| 符号 | 含义 | 单位 | 备注 |
|---|---|---|---|
| 待补充 | 待补充 | 待补充 | 待补充 |

## 四、数据处理与描述统计

待编辑：说明数据来源、字段含义、缺失值、异常值、单位转换、样本量和基础统计。建议引用数据审计结果表或更详细的数据审计表。

### 原始数据引用（非结果表证据）

{raw_block}

> 注意：本小节中的原始数据/附件文件名仅说明数据来源，不应被报告一致性审计当作 `03_结果表格/` 的结果表引用。真正支撑结论的结果表应在各小问“证据表”中列出。

## 五、模型建立、求解与结果分析

{section_text}

## 六、模型检验

待编辑：汇总 baseline、核心模型、敏感性/鲁棒性分析。必须说明检验结果支持或限制了哪些结论。

## 七、模型优缺点

### 优点

- 待编辑：结合本题模型结构和数据证据写具体优点。

### 缺点

- 待编辑：结合数据不足、假设限制、模型适用边界写具体缺点。

## 八、结论与建议

待编辑：按小问逐条给出最终答案和建议。不要新增没有证据支撑的结论。

## 参考文献

待编辑：列出数据来源、政策文件、论文或模型方法参考。

## 附录

待编辑：说明代码入口、关键结果表、图表清单和复现命令。
"""


def audit(project: Path, title: str) -> dict[str, Any]:
    questions = get_questions(project)
    all_tables = list_files(project, "03_结果表格", TABLE_EXTS)
    all_figures = list_files(project, "04_图表", FIGURE_EXTS)
    problem_text = read_text_safe(project / "06_过程记录" / "problem_analysis.md")
    raw_data_files = list_raw_data_files(project)
    raw_data_refs = extract_raw_data_refs(problem_text, raw_data_files)
    sections = [build_section(project, q, all_tables, all_figures) for q in questions]

    audit_json = load_json(project / "06_过程记录" / "一致性检查" / "auto_report_audit.json")
    quality_json = load_json(project / "06_过程记录" / "质量门禁" / "quality_gate_plus.json")
    coverage_json = load_json(project / "06_过程记录" / "问题覆盖" / "problem_coverage.json")
    interp_json = load_json(project / "06_过程记录" / "结果解释" / "result_interpretation_draft.json")

    global_warnings: list[str] = []
    if not questions:
        global_warnings.append("未能抽取小问清单，报告骨架无法按题目逐问拼装。")
    if audit_json.get("counts", {}).get("fail"):
        global_warnings.append("报告一致性审计存在 fail；本骨架只能作为修复草稿。")
    if quality_json.get("counts", {}).get("fail"):
        global_warnings.append("增强质量门禁存在 fail；需先补齐项目产物。")
    if coverage_json.get("counts", {}).get("missing_questions"):
        global_warnings.append("问题覆盖追踪存在漏答小问；本骨架已保留对应章节但需补证据。")
    if interp_json.get("counts", {}).get("drafts_without_tables"):
        global_warnings.append("结果解释草稿存在缺少表格证据的小问；对应章节不得直接定稿。")

    counts = {
        "questions": len(sections),
        "ready_sections": sum(1 for s in sections if s.completeness == "ready"),
        "partial_sections": sum(1 for s in sections if s.completeness == "partial"),
        "weak_sections": sum(1 for s in sections if s.completeness == "weak"),
        "tables_inventory": len(all_tables),
        "figures_inventory": len(all_figures),
        "raw_data_refs": len(raw_data_refs),
        "warn": sum(1 for s in sections if s.completeness != "ready") + len(global_warnings),
        "fail": 0 if sections else 1,
    }
    return {
        "generated_at": datetime.now().isoformat(timespec="seconds"),
        "project": str(project),
        "title": title,
        "counts": counts,
        "global_warnings": global_warnings,
        "raw_data_files": raw_data_files,
        "raw_data_refs": raw_data_refs,
        "sections": [asdict(s) for s in sections],
    }


def write_outputs(
    project: Path,
    summary: dict[str, Any],
    report_name: str,
    overwrite_report: bool = False,
) -> tuple[Path, Path, Path]:
    out_dir = project / "06_过程记录" / "报告拼装"
    out_dir.mkdir(parents=True, exist_ok=True)
    report_dir = project / "05_报告定稿"
    report_dir.mkdir(parents=True, exist_ok=True)

    json_path = out_dir / "report_section_assembly.json"
    md_path = out_dir / "report_section_assembly.md"
    report_path = report_dir / report_name

    sections = [Section(**s) for s in summary.get("sections", [])]
    report_text = build_report(project, sections, summary.get("title") or "数学建模报告")
    if overwrite_report or not report_path.exists():
        report_path.write_text(report_text, encoding="utf-8")
    json_path.write_text(json.dumps(summary, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    c = summary["counts"]
    lines: list[str] = []
    lines.append("# 证据优先报告拼装摘要\n\n")
    lines.append(f"生成时间：{summary['generated_at']}\n\n")
    lines.append(f"项目：`{summary['project']}`\n\n")
    lines.append(f"报告骨架：`{report_path.relative_to(project)}`\n\n")
    lines.append("## 汇总\n\n")
    lines.append(f"- 小问数：{c['questions']}\n- ready章节：{c['ready_sections']}\n- partial章节：{c['partial_sections']}\n- weak章节：{c['weak_sections']}\n- 结果表库存：{c['tables_inventory']}\n- 图表库存：{c['figures_inventory']}\n- 原始数据引用：{c.get('raw_data_refs', 0)}\n- warn：{c['warn']}\n- fail：{c['fail']}\n\n")
    if summary.get("global_warnings"):
        lines.append("## 全局风险\n\n")
        for w in summary["global_warnings"]:
            lines.append(f"- ⚠️ {w}\n")
        lines.append("\n")
    if summary.get("raw_data_refs"):
        lines.append("## 原始数据引用（非结果表证据）\n\n")
        for ref in summary["raw_data_refs"]:
            lines.append(f"- `{ref}`\n")
        lines.append("\n")
    lines.append("## 逐问章节状态\n\n| 小问 | 状态 | 结果表 | 图表 | 风险数 |\n|---|---|---:|---:|---:|\n")
    for s in summary.get("sections", []):
        lines.append(f"| {s['qid']} | {s['completeness']} | {len(s.get('tables', []))} | {len(s.get('figures', []))} | {len(s.get('caveats', []))} |\n")
    lines.append("\n## 下一步\n\n- 打开报告骨架，逐段替换“待编辑”。\n- 所有直接结论必须回指结果表或图表。\n- 若章节状态不是 ready，先补表格/图表证据，再定稿。\n")
    md_path.write_text("".join(lines), encoding="utf-8")
    return report_path, json_path, md_path


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("project")
    parser.add_argument("--title", default="数学建模报告", help="Report title")
    parser.add_argument("--report-name", default="report_draft.md", help="Markdown report filename under 05_报告定稿")
    parser.add_argument("--force-report", action="store_true", help="Overwrite an existing report draft")
    parser.add_argument("--strict", action="store_true", help="Return non-zero if warnings exist")
    args = parser.parse_args()

    project = Path(args.project).expanduser().resolve()
    if not project.exists():
        print(f"Project not found: {project}", file=sys.stderr)
        return 2
    summary = audit(project, args.title)
    report_path, json_path, md_path = write_outputs(
        project,
        summary,
        args.report_name,
        overwrite_report=args.force_report,
    )
    c = summary["counts"]
    print(f"Report draft: {report_path}")
    print(f"Assembly summary: {md_path}")
    print(f"Assembly json: {json_path}")
    print(f"Questions: {c['questions']}, ready={c['ready_sections']}, partial={c['partial_sections']}, weak={c['weak_sections']}, fail={c['fail']}, warn={c['warn']}")
    if c["fail"]:
        return 1
    if args.strict and c["warn"]:
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
