# 报告-结果自动一致性检查

本文件定义 `finalize_modeling_project.py` 的报告资产一致性检查口径，用于减少建模报告终稿中的低级错误。

## 1. 目标

检查报告文本中的图表/结果文件引用是否和项目目录中的真实文件一致：

- `05_报告定稿/*.md/*.tex`：可自动解析；
- `04_图表/*.{png,jpg,jpeg,pdf,svg}`：图表资产；
- `03_结果表格/*.{csv,xlsx,xls,json}`：结果表格资产。

DOCX/PDF 暂不做深度解析，只检查文件存在性，并在 strict 模式下提示需要人工核对。

## 2. 能发现的问题

| 问题 | 示例 |
|---|---|
| 报告引用了不存在的图 | `![图1](old_fig.png)` 但图表目录没有 `old_fig.png` |
| 报告引用了不存在的结果表 | 正文写 `model_results.csv` 但结果目录没有该文件 |
| 图表/结果未被报告引用 | 目录里有旧结果，报告没有引用，可能是版本残留 |
| 图号/表号缺失 | 报告没有“图1/表1”等编号 |
| DOCX/PDF 无法自动解析 | 提醒人工核对，不能假装通过 |

## 3. 使用方式

普通检查：

```bash
python ~/.hermes/skills/data-science/mathematical-modeling-agent/scripts/finalize_modeling_project.py . --entry 02_代码/03_model_main.py
```

严格检查：

```bash
python ~/.hermes/skills/data-science/mathematical-modeling-agent/scripts/finalize_modeling_project.py . --strict --entry 02_代码/03_model_main.py
```

生成 zip 包：

```bash
python ~/.hermes/skills/data-science/mathematical-modeling-agent/scripts/finalize_modeling_project.py . --zip --entry 02_代码/03_model_main.py
```

关闭报告资产交叉检查：

```bash
python ~/.hermes/skills/data-science/mathematical-modeling-agent/scripts/finalize_modeling_project.py . --no-crosscheck
```

## 4. 判定口径

- 报告显式引用不存在的图/结果表：`fail`。
- 报告提到原始附件或数据字典文件，例如 `01_原始数据/*.csv`、`data_dictionary.csv`、`Wimbledon_featured_matches.csv`，不按结果表缺失处理；脚本会记录 `raw_table_refs_ignored`。
- 只有 DOCX/PDF，无 Markdown/TeX 可解析文本：`warn`，需要人工核对。
- 目录中存在未被显式引用的图/表：`warn`，需要判断是否为旧结果残留。
- 引用全部存在：`pass`。

## 5. 局限

- 该检查不能判断数值本身是否正确，只能检查文件引用一致性。
- 对 DOCX/PDF 深度解析需要额外依赖，当前避免引入重依赖。
- 如果报告只写“图1/表1”但不写文件名，脚本只能检查编号存在，无法精确对应具体文件。

## 6. 工作流要求

最终报告建议保留一个 Markdown 或 LaTeX 源文件，即使最终提交 DOCX/PDF，也便于自动检查图表和结果引用一致性。
