# 项目状态自动推进器

`update_project_state.py` 用于根据项目中真实存在的产物自动判断 S0-S8 状态，并写回：

```text
06_过程记录/状态机/PROJECT_STATE.md
project_meta.json
```

## 使用方式

在项目根目录运行：

```bash
python ~/.hermes/skills/data-science/mathematical-modeling-agent/scripts/update_project_state.py .
```

或使用项目脚手架自带入口：

```bash
python 02_代码/07_update_state.py
```

严格要求最终提交包完成：

```bash
python ~/.hermes/skills/data-science/mathematical-modeling-agent/scripts/update_project_state.py . --strict
```

## 状态判据

| 状态 | 判据 |
|---|---|
| S0 材料获取 | `00_题目与资料/*` 或 `01_原始数据/*` 存在 |
| S1 题目解析完成 | `06_过程记录/problem_analysis.md` 有实质内容 |
| S2 数据审计完成 | `03_结果表格/data_audit.csv` 存在 |
| S3 基线模型完成 | `03_结果表格/*baseline*` 或 `*基线*` 存在 |
| S4 核心模型完成 | `03_结果表格/*model_results*` / `*main_model*` / `*core_model*` / `*主模型*` / `*核心模型*` 存在 |
| S5 敏感性/鲁棒性完成 | `03_结果表格/*sensitivity*` / `*robust*` / `*敏感*` / `*鲁棒*` 存在 |
| S6 报告初稿完成 | `05_报告定稿/*.md/*.docx/*.pdf/*.tex` 存在 |
| S7 一致性检查完成 | `auto_report_audit.md` 和 `report_consistency_check.md` 存在 |
| S8 最终提交包完成 | `README_submit.md`、`SHA256SUMS.txt`、`submission_manifest.json` 存在 |

## 重要口径

- 状态推进只看证据文件，不听口头声明。
- `当前连续完成状态` 只计算从 S0 开始连续完成的最高状态；如果 S3 缺失，即使 S4 有文件，也不会把项目视作连续完成到 S4。
- 脚本不评价模型是否正确，只判断流程产物是否闭环。
- 如果用户发现状态误判，应优先补充更明确的产物文件，而不是强行改状态文本。
