#!/usr/bin/env python3
"""Finalize and validate a mathematical modeling project submission package.

Usage:
    python finalize_modeling_project.py /path/to/project --report 05_报告定稿/report.pdf
    python finalize_modeling_project.py /path/to/project --strict --entry 02_代码/03_model_main.py

The script does not modify source reports, code, results, figures, or raw data.
It builds a clean staged package, validates its manifest and SHA256 checksums,
and replaces 07_提交包 only after validation succeeds. It can also cross-check
text report references against actual result and figure files.
"""
from __future__ import annotations

import argparse
import json
import re
import shutil
import sys
import uuid
import zipfile
from dataclasses import asdict, dataclass
from datetime import datetime
from pathlib import Path

from submission_package_contract import (
    PACKAGE_SCHEMA_VERSION,
    validate_submission_package,
    write_checksums,
)

DEFAULT_DIRS = [
    "00_题目与资料",
    "01_原始数据",
    "02_代码",
    "03_结果表格",
    "04_图表",
    "05_报告定稿",
    "06_过程记录",
    "07_提交包",
]
REPORT_EXTS = {".pdf", ".docx", ".md", ".tex"}
TABLE_EXTS = {".csv", ".xlsx", ".xls", ".json"}
FIGURE_EXTS = {".png", ".jpg", ".jpeg", ".pdf", ".svg"}


@dataclass
class Check:
    name: str
    status: str  # pass/warn/fail
    detail: str


@dataclass
class BuildResult:
    published: bool
    final_dir: Path
    checks: list[Check]
    validation_reasons: list[str]


def copy_if_exists(src: Path, dst: Path) -> list[Path]:
    copied: list[Path] = []
    if not src.exists():
        return copied
    if src.is_file():
        dst.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(src, dst)
        copied.append(dst)
    elif src.is_dir():
        for p in src.rglob("*"):
            if p.is_file():
                rel = p.relative_to(src)
                target = dst / rel
                target.parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(p, target)
                copied.append(target)
    return copied


def find_reports(project: Path) -> list[Path]:
    report_dir = project / "05_报告定稿"
    if not report_dir.exists():
        return []
    return sorted([p for p in report_dir.rglob("*") if p.is_file() and p.suffix.lower() in REPORT_EXTS])


def list_files(project: Path, rel: str, exts: set[str] | None = None) -> list[Path]:
    d = project / rel
    if not d.exists():
        return []
    files = [p for p in d.rglob("*") if p.is_file()]
    if exts is not None:
        files = [p for p in files if p.suffix.lower() in exts]
    return sorted(files)


def read_text_safe(path: Path) -> str:
    try:
        return path.read_text(encoding="utf-8", errors="ignore")
    except Exception:
        return ""




def normalize_stem(text: str) -> str:
    """Normalize filenames/tokens for loose report reference matching."""
    return re.sub(r"[^0-9a-zA-Z\u4e00-\u9fff]+", "", text).lower()


def normalize_ref_path(text: str) -> str:
    return text.split("#", 1)[0].split("?", 1)[0].strip().strip('"\'')


def is_raw_or_reference_table_ref(ref: str) -> bool:
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


def extract_report_tokens(reports: list[Path]) -> tuple[set[str], set[str], dict[str, int]]:
    """Extract lightweight figure/table/file references from Markdown/TeX reports.

    Binary DOCX/PDF are intentionally not parsed here to avoid heavy dependencies;
    their existence is still checked. For Markdown/TeX, this catches the common
    failure mode where text cites old/nonexistent figure or result filenames.
    """
    fig_tokens: set[str] = set()
    table_tokens: set[str] = set()
    stats = {"text_reports": 0, "numeric_figure_refs": 0, "numeric_table_refs": 0}
    raw_table_tokens: set[str] = set()
    for report in reports:
        if report.suffix.lower() not in {".md", ".tex"}:
            continue
        stats["text_reports"] += 1
        text = read_text_safe(report)
        # Markdown images: ![caption](../04_图表/fig1.png)
        for m in re.findall(r"!\[[^\]]*\]\(([^)]+)\)", text):
            stem = Path(m.split("#", 1)[0].split("?", 1)[0]).stem
            if stem:
                fig_tokens.add(normalize_stem(stem))
        # LaTeX includegraphics
        for m in re.findall(r"\\includegraphics(?:\[[^\]]*\])?\{([^}]+)\}", text):
            stem = Path(m).stem
            if stem:
                fig_tokens.add(normalize_stem(stem))
        # Explicit filenames in text.
        for m in re.findall(r"([\w\-\u4e00-\u9fff./]+\.(?:png|jpg|jpeg|svg|pdf))", text, flags=re.I):
            fig_tokens.add(normalize_stem(Path(m).stem))
        for m in re.findall(r"([\w\-\u4e00-\u9fff./]+\.(?:csv|xlsx|xls|json))", text, flags=re.I):
            stem = normalize_stem(Path(normalize_ref_path(m)).stem)
            if is_raw_or_reference_table_ref(m):
                raw_table_tokens.add(stem)
            else:
                table_tokens.add(stem)
        # Numeric captions/references.
        fig_nums = re.findall(r"(?:图|Figure\s*)(\d+)", text, flags=re.I)
        tab_nums = re.findall(r"(?:表|Table\s*)(\d+)", text, flags=re.I)
        stats["numeric_figure_refs"] += len(fig_nums)
        stats["numeric_table_refs"] += len(tab_nums)
    stats["raw_table_refs_ignored"] = len(raw_table_tokens)
    return fig_tokens, table_tokens, stats


def cross_check_report_assets(reports: list[Path], figures: list[Path], tables: list[Path]) -> list[Check]:
    checks: list[Check] = []
    fig_tokens, table_tokens, stats = extract_report_tokens(reports)
    if stats["text_reports"] == 0:
        checks.append(Check("report_asset_crosscheck", "warn", "未解析到 Markdown/TeX 报告；DOCX/PDF 仅检查存在性，需人工核对图表与数值一致性"))
        return checks

    figure_stems = {normalize_stem(p.stem): p for p in figures}
    table_stems = {normalize_stem(p.stem): p for p in tables}

    missing_figs = sorted([t for t in fig_tokens if t and t not in figure_stems])
    missing_tables = sorted([t for t in table_tokens if t and t not in table_stems])
    unreferenced_figs = sorted([p.name for k, p in figure_stems.items() if fig_tokens and k not in fig_tokens])
    unreferenced_tables = sorted([p.name for k, p in table_stems.items() if table_tokens and k not in table_tokens and p.name != "data_audit.csv"])

    if missing_figs:
        checks.append(Check("report_referenced_figures_exist", "fail", "报告引用了不存在的图文件 token: " + ", ".join(missing_figs[:20])))
    else:
        checks.append(Check("report_referenced_figures_exist", "pass", f"{len(fig_tokens)} referenced figure token(s) checked"))

    if missing_tables:
        checks.append(Check("report_referenced_tables_exist", "fail", "报告引用了不存在的结果表 token: " + ", ".join(missing_tables[:20])))
    else:
        checks.append(Check("report_referenced_tables_exist", "pass", f"{len(table_tokens)} referenced table token(s) checked"))

    if stats.get("raw_table_refs_ignored", 0):
        checks.append(Check("raw_table_refs_ignored", "pass", f"ignored {stats['raw_table_refs_ignored']} raw/reference data table token(s)"))

    if unreferenced_figs:
        checks.append(Check("unreferenced_figure_files", "warn", "图表目录存在未被文本报告显式引用的文件: " + ", ".join(unreferenced_figs[:20])))
    else:
        checks.append(Check("unreferenced_figure_files", "pass", f"{len(figures)} figure file(s) referenced or no explicit filename refs"))

    if unreferenced_tables:
        checks.append(Check("unreferenced_result_tables", "warn", "结果目录存在未被文本报告显式引用的文件: " + ", ".join(unreferenced_tables[:20])))
    else:
        checks.append(Check("unreferenced_result_tables", "pass", f"{len(tables)} table file(s) referenced or audit-only"))

    checks.append(Check("numeric_caption_refs", "pass" if (stats["numeric_figure_refs"] or stats["numeric_table_refs"]) else "warn", f"figure refs={stats['numeric_figure_refs']}, table refs={stats['numeric_table_refs']}"))
    return checks


def create_zip_archive(final_dir: Path) -> Path:
    zip_path = final_dir / "submission_package.zip"
    with zipfile.ZipFile(zip_path, "w", compression=zipfile.ZIP_DEFLATED) as zf:
        for p in sorted(final_dir.rglob("*")):
            if p.is_file() and p != zip_path:
                zf.write(p, p.relative_to(final_dir))
    return zip_path


def validate_project(project: Path, reports: list[Path], entry: str | None, crosscheck_assets: bool = True) -> list[Check]:
    checks: list[Check] = []
    for d in DEFAULT_DIRS:
        p = project / d
        checks.append(Check(f"standard_dir:{d}", "pass" if p.exists() else "fail", str(p)))

    tables = list_files(project, "03_结果表格", TABLE_EXTS)
    figures = list_files(project, "04_图表", FIGURE_EXTS)
    code = list_files(project, "02_代码", None)
    state = project / "06_过程记录/状态机/PROJECT_STATE.md"
    consistency = project / "06_过程记录/一致性检查/report_consistency_check.md"
    data_audit = project / "03_结果表格/data_audit.csv"

    checks.append(Check("report_exists", "pass" if reports else "fail", f"{len(reports)} report file(s)"))
    checks.append(Check("result_tables_exist", "pass" if tables else "warn", f"{len(tables)} table file(s)"))
    checks.append(Check("figures_exist", "pass" if figures else "warn", f"{len(figures)} figure file(s)"))
    checks.append(Check("code_exists", "pass" if code else "warn", f"{len(code)} code file(s)"))
    checks.append(Check("data_audit_exists", "pass" if data_audit.exists() else "warn", str(data_audit)))
    checks.append(Check("state_file_exists", "pass" if state.exists() else "warn", str(state)))
    checks.append(Check("consistency_check_exists", "pass" if consistency.exists() else "warn", str(consistency)))

    if entry:
        ep = Path(entry)
        if not ep.is_absolute():
            ep = project / ep
        checks.append(Check("entry_exists", "pass" if ep.exists() else "fail", str(ep)))

    if crosscheck_assets:
        checks.extend(cross_check_report_assets(reports, figures, tables))

    return checks


def write_readme(project: Path, final_dir: Path, copied: list[Path], checks: list[Check], entry: str | None) -> None:
    rel_files = sorted({p.relative_to(final_dir) for p in copied if p.exists()})
    lines: list[str] = []
    lines.append("# README_submit\n\n")
    lines.append(f"生成时间：{datetime.now().isoformat(timespec='seconds')}\n\n")
    lines.append(f"项目目录：`{project}`\n\n")
    lines.append("## 文件清单\n\n")
    if rel_files:
        for p in rel_files:
            lines.append(f"- `{p}`\n")
    else:
        lines.append("- 暂无复制文件。\n")
    lines.append("\n## 复现说明\n\n")
    if entry:
        lines.append(f"建议代码入口：`{entry}`\n\n")
        lines.append("```bash\n")
        lines.append(f"python {entry}\n")
        lines.append("```\n")
    else:
        lines.append("未指定代码入口。请查看 `source_code/` 或项目 `02_代码/`。\n")
    lines.append("\n## 自动检查结果\n\n")
    lines.append("| 检查项 | 状态 | 说明 |\n|---|---|---|\n")
    for c in checks:
        mark = {"pass": "✅", "warn": "⚠️", "fail": "❌"}.get(c.status, c.status)
        lines.append(f"| {c.name} | {mark} {c.status} | {c.detail} |\n")
    (final_dir / "README_submit.md").write_text("".join(lines), encoding="utf-8")


def build_submission_package(
    project: Path,
    reports: list[Path] | None = None,
    entry: str | None = None,
    include_raw_data: bool = False,
    include_code: bool = True,
    create_zip: bool = False,
    crosscheck_assets: bool = True,
    strict: bool = False,
) -> BuildResult:
    project = project.expanduser().resolve()
    final_dir = project / "07_提交包"
    report_paths = list(reports) if reports is not None else find_reports(project)
    existing_reports = [path for path in report_paths if path.exists() and path.is_file()]
    checks = validate_project(project, existing_reports, entry, crosscheck_assets=crosscheck_assets)
    for report_path in report_paths:
        if not report_path.exists() or not report_path.is_file():
            checks.append(Check("report_path_valid", "fail", f"报告文件不存在：{report_path}"))

    fail_count = sum(check.status == "fail" for check in checks)
    warn_count = sum(check.status == "warn" for check in checks)
    if fail_count or (strict and warn_count):
        reasons = [
            f"{check.status} check {check.name}: {check.detail}"
            for check in checks
            if check.status == "fail" or (strict and check.status == "warn")
        ]
        return BuildResult(False, final_dir, checks, reasons)

    token = uuid.uuid4().hex
    staging_dir = project / f"07_提交包.staging-{token}"
    backup_dir = project / f"07_提交包.backup-{token}"
    copied: list[Path] = []
    try:
        staging_dir.mkdir(parents=True)
        for report_path in existing_reports:
            copied += copy_if_exists(report_path, staging_dir / report_path.name)
        copied += copy_if_exists(project / "03_结果表格", staging_dir / "results_tables")
        copied += copy_if_exists(project / "04_图表", staging_dir / "figures")
        if include_code:
            copied += copy_if_exists(project / "02_代码", staging_dir / "source_code")
        if include_raw_data:
            copied += copy_if_exists(project / "01_原始数据", staging_dir / "raw_data")

        write_readme(project, staging_dir, copied, checks, entry)
        if create_zip:
            copied.append(create_zip_archive(staging_dir))

        copied_files = [
            path.relative_to(staging_dir).as_posix()
            for path in sorted(set(copied))
            if path.is_file()
        ]
        package_files = sorted(
            {
                path.relative_to(staging_dir).as_posix()
                for path in staging_dir.rglob("*")
                if path.is_file()
            }
            | {"submission_manifest.json"}
        )
        manifest = {
            "schema_version": PACKAGE_SCHEMA_VERSION,
            "generated_at": datetime.now().isoformat(timespec="seconds"),
            "project": str(project),
            "final_dir": str(final_dir),
            "options": {
                "include_code": include_code,
                "include_raw_data": include_raw_data,
                "create_zip": create_zip,
                "crosscheck_assets": crosscheck_assets,
                "strict": strict,
            },
            "copied_files": copied_files,
            "package_files": package_files,
            "checks": [asdict(check) for check in checks],
            "validation_counts": {
                "pass": sum(check.status == "pass" for check in checks),
                "warn": warn_count,
                "fail": fail_count,
            },
            "package_valid": True,
            "checksum_algorithm": "sha256",
            "checksum_file": "SHA256SUMS.txt",
        }
        (staging_dir / "submission_manifest.json").write_text(
            json.dumps(manifest, ensure_ascii=False, indent=2) + "\n",
            encoding="utf-8",
        )
        write_checksums(staging_dir, package_files)
        validation = validate_submission_package(staging_dir)
        if not validation.valid:
            return BuildResult(False, final_dir, checks, validation.reasons)

        if final_dir.exists():
            final_dir.rename(backup_dir)
        try:
            staging_dir.rename(final_dir)
        except Exception:
            if backup_dir.exists() and not final_dir.exists():
                backup_dir.rename(final_dir)
            raise
        if backup_dir.exists():
            shutil.rmtree(backup_dir)
        return BuildResult(True, final_dir, checks, [])
    except Exception as exc:
        return BuildResult(False, final_dir, checks, [f"package build failed: {exc}"])
    finally:
        if staging_dir.exists():
            shutil.rmtree(staging_dir)
        if backup_dir.exists() and final_dir.exists():
            shutil.rmtree(backup_dir)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("project", help="Project directory")
    parser.add_argument("--report", action="append", help="Report path relative to project or absolute; can repeat", default=None)
    parser.add_argument("--entry", help="Code entry path relative to project, e.g. 02_代码/03_model_main.py", default=None)
    parser.add_argument("--include-raw-data", action="store_true", help="Copy raw data into submission package (only if allowed)")
    parser.add_argument("--no-code", action="store_true", help="Do not copy code")
    parser.add_argument("--strict", action="store_true", help="Return non-zero on warnings as well as failures")
    parser.add_argument("--no-crosscheck", action="store_true", help="Disable lightweight Markdown/TeX report asset cross-check")
    parser.add_argument("--zip", action="store_true", help="Create 07_提交包/submission_package.zip after files are copied")
    args = parser.parse_args()

    project = Path(args.project).expanduser().resolve()
    if not project.exists():
        print(f"Project not found: {project}", file=sys.stderr)
        return 2
    reports: list[Path] | None = None
    if args.report:
        reports = []
        for item in args.report:
            path = Path(item).expanduser()
            reports.append(path if path.is_absolute() else project / path)

    result = build_submission_package(
        project,
        reports=reports,
        entry=args.entry,
        include_raw_data=args.include_raw_data,
        include_code=not args.no_code,
        create_zip=args.zip,
        crosscheck_assets=not args.no_crosscheck,
        strict=args.strict,
    )
    fail_count = sum(check.status == "fail" for check in result.checks)
    warn_count = sum(check.status == "warn" for check in result.checks)
    print(f"Final package: {result.final_dir}")
    print(f"Checks: {len(result.checks)} total, {fail_count} fail, {warn_count} warn")
    if not result.published:
        print("Package not published:")
        for reason in result.validation_reasons:
            print(f"- {reason}")
        return 1
    print("Ready: validated package published")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
