#!/usr/bin/env python3
"""Create a standardized mathematical modeling project scaffold.

Usage:
    python create_modeling_project.py "2026-国赛-A题" --base ~/Documents/数学建模
    python create_modeling_project.py "2026-国赛-A题" --base ~/Documents/数学建模 --force

This script creates a modeling project with state tracking, quality gates,
report consistency checklist, and executable starter scripts. It never deletes
existing project files. Existing files are preserved unless --force is passed.
"""
from __future__ import annotations

import argparse
import datetime as _dt
import json
import subprocess
import sys
from pathlib import Path

DIRS = [
    "00_题目与资料",
    "01_原始数据",
    "02_代码",
    "03_结果表格",
    "04_图表",
    "05_报告定稿",
    "06_过程记录",
    "06_过程记录/质量门禁",
    "06_过程记录/问题覆盖",
    "06_过程记录/结果解释",
    "06_过程记录/报告拼装",
    "06_过程记录/修复建议",
    "06_过程记录/model_skeleton",
    "06_过程记录/领域checker",
    "06_过程记录/竞赛质控",
    "06_过程记录/状态机",
    "06_过程记录/一致性检查",
    "06_过程记录/失败模式排雷",
    "07_提交包",
    "08_候选方案",
]

README = """# {project_name}

创建时间：{date}

## 目录结构

- `00_题目与资料/`：题面、附件说明、参考资料
- `01_原始数据/`：原始数据，只读不手改
- `02_代码/`：Python/R/Matlab 等代码
- `03_结果表格/`：CSV/XLSX/JSON 结果
- `04_图表/`：PNG/PDF/SVG 图表
- `05_报告定稿/`：DOCX/PDF/LaTeX/Markdown
- `06_过程记录/`：草稿、实验日志、状态机、一致性检查、竞赛质控与失败模式排雷
- `07_提交包/`：最终提交文件
- `08_候选方案/`：AIDE 式候选模型提交与父子改进分支

## 当前状态

当前状态：S0 材料获取

状态记录见：`06_过程记录/状态机/PROJECT_STATE.md`

## 执行顺序

1. 题目解析与数据审计
2. 数据清洗与特征构造
3. 基线模型
4. 核心模型
5. 敏感性/鲁棒性分析
6. 报告一致性检查
7. 提交包生成

## 复现命令

```bash
python 02_代码/00_data_audit.py
python 02_代码/01_preprocess.py
python 02_代码/02_baseline.py
python 02_代码/03_model_main.py
python 02_代码/04_sensitivity.py
python 02_代码/05_make_figures.py
python 02_代码/15_model_skeleton.py --write-code
python 02_代码/16_domain_checker_templates.py
python 02_代码/17_contest_qc.py --init --phase early
python 02_代码/06_quality_gate.py
python 02_代码/08_pipeline.py --skip-finalize
python 02_代码/07_update_state.py
python 02_代码/09_problem_coverage.py
python 02_代码/10_result_interpretation.py
python 02_代码/11_report_assembler.py
python 02_代码/12_repair_advisor.py
python 02_代码/14_competition_evidence.py
python 02_代码/19_candidate_solution_tree.py init --objective-metric objective --direction maximize
python 02_代码/18_contest_evidence_sync.py --dry-run
python 02_代码/18_contest_evidence_sync.py
python 02_代码/17_contest_qc.py --phase final
python 02_代码/13_competition_readiness.py
python 02_代码/08_pipeline.py --zip
```

## 最终打包

```bash
python 02_代码/08_pipeline.py --zip
```
"""

PROJECT_STATE = """# PROJECT_STATE

> 状态机口径：S0 材料获取 → S1 题目解析 → S2 数据审计 → S3 基线模型 → S4 核心模型 → S5 敏感性/鲁棒性 → S6 报告初稿 → S7 一致性检查 → S8 最终提交包。

| 状态 | 完成? | 产物路径 | 证据/备注 |
|---|---|---|---|
| S0 材料获取 | 否 | `00_题目与资料/` | 题面、附件、数据字典是否齐全 |
| S1 题目解析完成 | 否 | `06_过程记录/problem_analysis.md` | 每问目标、变量、输出要求 |
| S2 数据审计完成 | 否 | `03_结果表格/data_audit.csv` | 行列数、缺失、重复、单位、异常 |
| S3 基线模型完成 | 否 | `03_结果表格/baseline_results.*` | 可运行 baseline 与 sanity check |
| S4 核心模型完成 | 否 | `03_结果表格/model_results.*` | 主模型结果与日志 |
| S5 敏感性/鲁棒性分析完成 | 否 | `03_结果表格/sensitivity_results.*` | 关键参数扰动/替代模型 |
| S6 报告初稿完成 | 否 | `05_报告定稿/` | 每问有结论，图表已引用 |
| S7 一致性检查完成 | 否 | `06_过程记录/一致性检查/report_consistency_check.md` | 题目-公式-代码-图表-摘要一致 |
| S8 最终提交包完成 | 否 | `07_提交包/` | README_submit.md 与 SHA256SUMS.txt |

## 当前阻塞项

- [ ] 待补充
"""

CONSISTENCY_CHECK = """# 报告一致性检查记录

| 检查项 | 通过? | 证据/文件 | 问题与修正 |
|---|---|---|---|
| 每个小问有明确答案 | 否 |  |  |
| 摘要核心数值来自最终表格 | 否 |  |  |
| 公式变量与代码变量一致 | 否 |  |  |
| 图表编号连续且正文引用 | 否 |  |  |
| 单位一致 | 否 |  |  |
| baseline 与核心模型均有结果 | 否 |  |  |
| 敏感性/鲁棒性分析存在 | 否 |  |  |
| 提交包文件齐全 | 否 |  |  |
"""

FAILURE_LOG = """# 失败模式排雷记录

| 风险 | 是否存在 | 证据 | 处理 |
|---|---|---|---|
| 题意理解偏差 | 未检查 |  |  |
| 数据字段/单位错误 | 未检查 |  |  |
| 重复测量当独立样本 | 未检查 |  |  |
| 数据泄漏 | 未检查 |  |  |
| 无 baseline | 未检查 |  |  |
| 复杂模型不可解释 | 未检查 |  |  |
| 结果与常识冲突 | 未检查 |  |  |
| 图表/正文/摘要不一致 | 未检查 |  |  |
"""

CANDIDATE_README = """# 候选方案目录

每个候选方案使用独立子目录，并至少包含 `solution.json`、`run_record.json`、`report.md` 和可哈希验证的证据文件。

候选树只读取已经运行产生的产物，不执行 `run_record.json` 中记录的命令。推荐先登记 baseline，再以父节点和改进假设创建有限深度分支。`selected` 只表示当前配置下最优的合格候选，不等于 `paper_ready`、`final_ready` 或 `competition_ready`。
"""

SCRIPT_TEMPLATES = {
    "00_data_audit.py": """from pathlib import Path\nimport csv\nimport json\n\nBASE = Path(__file__).resolve().parents[1]\nRAW = BASE / '01_原始数据'\nOUT = BASE / '03_结果表格'\nOUT.mkdir(exist_ok=True)\n\ndef audit_csv(path):\n    rows = 0\n    missing = 0\n    columns = []\n    with path.open('r', encoding='utf-8-sig', errors='ignore', newline='') as f:\n        reader = csv.reader(f)\n        for i, row in enumerate(reader):\n            if i == 0:\n                columns = [str(x) for x in row]\n                continue\n            rows += 1\n            missing += sum(1 for x in row if str(x).strip() == '')\n    return {'rows': rows, 'cols': len(columns), 'columns': '|'.join(columns), 'missing_cells': missing}\n\nrecords = []\nfor path in sorted(RAW.rglob('*')):\n    if not path.is_file() or path.name.startswith('~$'):\n        continue\n    info = {'file': str(path.relative_to(BASE)), 'suffix': path.suffix.lower(), 'size_bytes': path.stat().st_size}\n    try:\n        if path.suffix.lower() == '.csv':\n            info.update(audit_csv(path))\n        elif path.suffix.lower() in {'.xlsx', '.xls'}:\n            info['note'] = 'spreadsheet detected; install optional openpyxl/pandas or add problem-specific parser for deep audit'\n        elif path.suffix.lower() == '.json':\n            obj = json.loads(path.read_text(encoding='utf-8', errors='ignore'))\n            info['json_type'] = type(obj).__name__\n            if isinstance(obj, list):\n                info['rows'] = len(obj)\n    except Exception as e:\n        info['error'] = repr(e)\n    records.append(info)\n\nout = OUT / 'data_audit.csv'\nfields = sorted({k for r in records for k in r.keys()} | {'file', 'suffix', 'size_bytes'})\nwith out.open('w', encoding='utf-8-sig', newline='') as f:\n    writer = csv.DictWriter(f, fieldnames=fields)\n    writer.writeheader()\n    writer.writerows(records)\nprint(f'Wrote {out} with {len(records)} file records')\n""",
    "01_preprocess.py": """from pathlib import Path\n\nBASE = Path(__file__).resolve().parents[1]\nprint('TODO: preprocess raw data into processed datasets; never overwrite raw data')\n""",
    "02_baseline.py": """from pathlib import Path\nimport csv\nimport math\n\nBASE = Path(__file__).resolve().parents[1]\nRAW = BASE / '01_原始数据'\nOUT = BASE / '03_结果表格'\nOUT.mkdir(exist_ok=True)\n\ndef to_float(x):\n    try:\n        if x is None or str(x).strip() == '':\n            return None\n        v = float(str(x).replace(',', '').strip().rstrip('%'))\n        if str(x).strip().endswith('%'):\n            v /= 100.0\n        return v if math.isfinite(v) else None\n    except Exception:\n        return None\n\ndef summarize_csv(path):\n    with path.open('r', encoding='utf-8-sig', errors='ignore', newline='') as f:\n        rows = list(csv.DictReader(f))\n    if not rows:\n        return []\n    out = []\n    for col in rows[0].keys():\n        nums = [to_float(r.get(col)) for r in rows]\n        nums = [x for x in nums if x is not None]\n        if nums:\n            out.append({'source_file': str(path.relative_to(BASE)), 'column': col, 'count': len(nums), 'mean': sum(nums)/len(nums), 'min': min(nums), 'max': max(nums)})\n    return out\n\nrecords = []\nfor path in sorted(RAW.rglob('*.csv')):\n    records.extend(summarize_csv(path))\n\nout = OUT / 'baseline_results.csv'\nfields = ['source_file', 'column', 'count', 'mean', 'min', 'max']\nwith out.open('w', encoding='utf-8-sig', newline='') as f:\n    writer = csv.DictWriter(f, fieldnames=fields)\n    writer.writeheader()\n    writer.writerows(records)\nprint(f'Wrote {out} with {len(records)} numeric-column summaries')\n""",
    "03_model_main.py": """from pathlib import Path\nimport csv\nimport math\n\nBASE = Path(__file__).resolve().parents[1]\nOUT = BASE / '03_结果表格'\nOUT.mkdir(exist_ok=True)\nBASELINE = OUT / 'baseline_results.csv'\n\ndef to_float(x):\n    try:\n        v = float(str(x).replace(',', '').strip())\n        return v if math.isfinite(v) else None\n    except Exception:\n        return None\n\nrecords = []\nif BASELINE.exists():\n    with BASELINE.open('r', encoding='utf-8-sig', errors='ignore', newline='') as f:\n        for row in csv.DictReader(f):\n            mean = to_float(row.get('mean'))\n            mn = to_float(row.get('min'))\n            mx = to_float(row.get('max'))\n            spread = (mx - mn) if mn is not None and mx is not None else None\n            records.append({\n                'source_file': row.get('source_file', ''),\n                'indicator': row.get('column', ''),\n                'baseline_mean': mean,\n                'range': spread,\n                'model_note': 'lightweight baseline-derived placeholder; replace with problem-specific mathematical model after S1 analysis',\n            })\n\nout = OUT / 'model_results.csv'\nfields = ['source_file', 'indicator', 'baseline_mean', 'range', 'model_note']\nwith out.open('w', encoding='utf-8-sig', newline='') as f:\n    writer = csv.DictWriter(f, fieldnames=fields)\n    writer.writeheader()\n    writer.writerows(records)\nprint(f'Wrote {out} with {len(records)} rows; customize this script for the real model')\n""",
    "04_sensitivity.py": """from pathlib import Path\nimport csv\n\nBASE = Path(__file__).resolve().parents[1]\nOUT = BASE / '03_结果表格'\nOUT.mkdir(exist_ok=True)\nMODEL = OUT / 'model_results.csv'\n\nrecords = []\nif MODEL.exists():\n    with MODEL.open('r', encoding='utf-8-sig', errors='ignore', newline='') as f:\n        for row in csv.DictReader(f):\n            try:\n                base = float(row.get('baseline_mean') or 0)\n            except Exception:\n                continue\n            for factor in [0.9, 0.95, 1.05, 1.1]:\n                records.append({'indicator': row.get('indicator', ''), 'factor': factor, 'perturbed_value': base * factor})\n\nout = OUT / 'sensitivity_results.csv'\nfields = ['indicator', 'factor', 'perturbed_value']\nwith out.open('w', encoding='utf-8-sig', newline='') as f:\n    writer = csv.DictWriter(f, fieldnames=fields)\n    writer.writeheader()\n    writer.writerows(records)\nprint(f'Wrote {out} with {len(records)} perturbation rows')\n""",
    "05_make_figures.py": """from pathlib import Path\n\nBASE = Path(__file__).resolve().parents[1]\nFIG = BASE / '04_图表'\nFIG.mkdir(exist_ok=True)\nprint('TODO: generate figures with titles, axis labels, units, captions')\n""",
    "06_quality_gate.py": """from pathlib import Path\n\nBASE = Path(__file__).resolve().parents[1]\nrequired = {\n    'data audit': BASE / '03_结果表格' / 'data_audit.csv',\n    'state file': BASE / '06_过程记录' / '状态机' / 'PROJECT_STATE.md',\n    'consistency checklist': BASE / '06_过程记录' / '一致性检查' / 'report_consistency_check.md',\n}\nmissing = [f'{name}: {path}' for name, path in required.items() if not path.exists()]\nreports = list((BASE / '05_报告定稿').glob('*')) if (BASE / '05_报告定稿').exists() else []\nfigures = list((BASE / '04_图表').glob('*')) if (BASE / '04_图表').exists() else []\ntables = list((BASE / '03_结果表格').glob('*')) if (BASE / '03_结果表格').exists() else []\nprint('Quality gate summary')\nprint('reports:', len([p for p in reports if p.is_file()]))\nprint('figures:', len([p for p in figures if p.is_file()]))\nprint('tables:', len([p for p in tables if p.is_file()]))\nif missing:\n    print('Missing:')\n    for item in missing:\n        print('-', item)\n    raise SystemExit(1)\nprint('Basic project quality gate passed')\n""",
    "07_update_state.py": """from pathlib import Path\nimport subprocess\nimport sys\n\nBASE = Path(__file__).resolve().parents[1]\nSCRIPT = Path('__SKILL_SCRIPT_DIR__/update_project_state.py')\nraise SystemExit(subprocess.call([sys.executable, str(SCRIPT), str(BASE)]))\n""",
    "08_pipeline.py": """from pathlib import Path\nimport subprocess\nimport sys\n\nBASE = Path(__file__).resolve().parents[1]\nSCRIPT = Path('__SKILL_SCRIPT_DIR__/modeling_pipeline.py')\nraise SystemExit(subprocess.call([sys.executable, str(SCRIPT), str(BASE)] + sys.argv[1:]))\n""",
    "09_problem_coverage.py": """from pathlib import Path\nimport subprocess\nimport sys\n\nBASE = Path(__file__).resolve().parents[1]\nSCRIPT = Path('__SKILL_SCRIPT_DIR__/problem_coverage_tracker.py')\nraise SystemExit(subprocess.call([sys.executable, str(SCRIPT), str(BASE)] + sys.argv[1:]))\n""",
    "10_result_interpretation.py": """from pathlib import Path\nimport subprocess\nimport sys\n\nBASE = Path(__file__).resolve().parents[1]\nSCRIPT = Path('__SKILL_SCRIPT_DIR__/result_interpretation_helper.py')\nraise SystemExit(subprocess.call([sys.executable, str(SCRIPT), str(BASE)] + sys.argv[1:]))\n""",
    "11_report_assembler.py": """from pathlib import Path\nimport subprocess\nimport sys\n\nBASE = Path(__file__).resolve().parents[1]\nSCRIPT = Path('__SKILL_SCRIPT_DIR__/report_section_assembler.py')\nraise SystemExit(subprocess.call([sys.executable, str(SCRIPT), str(BASE)] + sys.argv[1:]))\n""",
    "12_repair_advisor.py": """from pathlib import Path\nimport subprocess\nimport sys\n\nBASE = Path(__file__).resolve().parents[1]\nSCRIPT = Path('__SKILL_SCRIPT_DIR__/repair_advisor.py')\nraise SystemExit(subprocess.call([sys.executable, str(SCRIPT), str(BASE)] + sys.argv[1:]))\n""",
    "13_competition_readiness.py": """from pathlib import Path\nimport subprocess\nimport sys\n\nBASE = Path(__file__).resolve().parents[1]\nSCRIPT = Path('__SKILL_SCRIPT_DIR__/competition_readiness_gate.py')\nraise SystemExit(subprocess.call([sys.executable, str(SCRIPT), str(BASE)] + sys.argv[1:]))\n""",
    "14_competition_evidence.py": """from pathlib import Path\nimport subprocess\nimport sys\n\nBASE = Path(__file__).resolve().parents[1]\nSCRIPT = Path('__SKILL_SCRIPT_DIR__/competition_evidence_builder.py')\nraise SystemExit(subprocess.call([sys.executable, str(SCRIPT), str(BASE)] + sys.argv[1:]))\n""",
    "15_model_skeleton.py": """from pathlib import Path\nimport subprocess\nimport sys\n\nBASE = Path(__file__).resolve().parents[1]\nSCRIPT = Path('__SKILL_SCRIPT_DIR__/model_skeleton_router.py')\nraise SystemExit(subprocess.call([sys.executable, str(SCRIPT), str(BASE)] + sys.argv[1:]))\n""",
    "16_domain_checker_templates.py": """from pathlib import Path\nimport subprocess\nimport sys\n\nBASE = Path(__file__).resolve().parents[1]\nSCRIPT = Path('__SKILL_SCRIPT_DIR__/domain_checker_template_builder.py')\nraise SystemExit(subprocess.call([sys.executable, str(SCRIPT), str(BASE)] + sys.argv[1:]))\n""",
    "17_contest_qc.py": """from pathlib import Path\nimport subprocess\nimport sys\n\nBASE = Path(__file__).resolve().parents[1]\nSCRIPT = Path('__SKILL_SCRIPT_DIR__/contest_qc_gate.py')\nraise SystemExit(subprocess.call([sys.executable, str(SCRIPT), str(BASE)] + sys.argv[1:]))\n""",
    "18_contest_evidence_sync.py": """from pathlib import Path\nimport subprocess\nimport sys\n\nBASE = Path(__file__).resolve().parents[1]\nSCRIPT = Path('__SKILL_SCRIPT_DIR__/contest_evidence_sync.py')\nraise SystemExit(subprocess.call([sys.executable, str(SCRIPT), str(BASE)] + sys.argv[1:]))\n""",
    "19_candidate_solution_tree.py": """from pathlib import Path\nimport subprocess\nimport sys\n\nBASE = Path(__file__).resolve().parents[1]\nSCRIPT = Path('__SKILL_SCRIPT_DIR__/candidate_solution_tree.py')\nraise SystemExit(subprocess.call([sys.executable, str(SCRIPT), sys.argv[1], str(BASE)] + sys.argv[2:])) if len(sys.argv) > 1 else 2\n""",
}

REQ = """# Core scaffold uses only Python stdlib for data_audit/baseline/model_main/sensitivity.
# Install optional packages only when the chosen model/report workflow needs them.
pandas
numpy
scipy
matplotlib
openpyxl
# Optional heavy/ML extras:
# scikit-learn
# seaborn
"""


def write_text(path: Path, content: str, force: bool = False) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    if force or not path.exists():
        path.write_text(content, encoding="utf-8")


def create_project(project_name: str, base: Path, force: bool = False) -> Path:
    project_dir = base.expanduser() / project_name
    project_dir.mkdir(parents=True, exist_ok=True)
    for d in DIRS:
        (project_dir / d).mkdir(parents=True, exist_ok=True)

    today = _dt.date.today().isoformat()
    write_text(project_dir / "README.md", README.format(project_name=project_name, date=today), force=force)
    write_text(project_dir / "requirements.txt", REQ, force=force)
    write_text(project_dir / "06_过程记录/状态机/PROJECT_STATE.md", PROJECT_STATE, force=force)
    write_text(project_dir / "06_过程记录/一致性检查/report_consistency_check.md", CONSISTENCY_CHECK, force=force)
    write_text(project_dir / "06_过程记录/失败模式排雷/failure_pattern_log.md", FAILURE_LOG, force=force)
    write_text(project_dir / "06_过程记录/problem_analysis.md", "# 题目解析\n\n## 小问拆解\n\n## 数据清单\n\n## 输出要求\n\n## 题型路由\n", force=force)
    write_text(project_dir / "08_候选方案/README.md", CANDIDATE_README, force=force)

    metadata = {
        "project_name": project_name,
        "created_at": today,
        "state": "S0 材料获取",
        "skill": "mathematical-modeling-agent",
        "state_file": "06_过程记录/状态机/PROJECT_STATE.md",
        "quality_gate": "02_代码/06_quality_gate.py",
        "state_updater": "02_代码/07_update_state.py",
        "pipeline_runner": "02_代码/08_pipeline.py",
        "problem_coverage_tracker": "02_代码/09_problem_coverage.py",
        "result_interpretation_helper": "02_代码/10_result_interpretation.py",
        "report_section_assembler": "02_代码/11_report_assembler.py",
        "repair_advisor": "02_代码/12_repair_advisor.py",
        "competition_readiness_gate": "02_代码/13_competition_readiness.py",
        "competition_evidence_builder": "02_代码/14_competition_evidence.py",
        "model_skeleton_router": "02_代码/15_model_skeleton.py",
        "domain_checker_template_builder": "02_代码/16_domain_checker_templates.py",
        "contest_qc_gate": "02_代码/17_contest_qc.py",
        "contest_evidence_sync": "02_代码/18_contest_evidence_sync.py",
        "candidate_solution_tree": "02_代码/19_candidate_solution_tree.py",
        "quality_gate_plus": "scripts/quality_gate_plus.py",
    }
    write_text(project_dir / "project_meta.json", json.dumps(metadata, ensure_ascii=False, indent=2) + "\n", force=force)

    code_dir = project_dir / "02_代码"
    skill_scripts_dir = Path(__file__).resolve().parent
    for name, content in SCRIPT_TEMPLATES.items():
        content = content.replace(
            "__SKILL_SCRIPT_DIR__",
            str(skill_scripts_dir),
        )
        write_text(code_dir / name, content, force=force)

    qc_script = skill_scripts_dir / "contest_qc_gate.py"
    qc_command = [sys.executable, str(qc_script), str(project_dir), "--init", "--phase", "early"]
    if force:
        qc_command.append("--force-templates")
    subprocess.run(qc_command, check=True)

    return project_dir


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("project_name")
    parser.add_argument("--base", default="~/Documents/数学建模")
    parser.add_argument("--force", action="store_true", help="overwrite scaffold files but never delete data")
    args = parser.parse_args()

    path = create_project(args.project_name, Path(args.base), force=args.force)
    print(path)


if __name__ == "__main__":
    main()
