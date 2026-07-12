# 证据优先报告拼装器 report_section_assembler

`report_section_assembler.py` 用于把题目解析、逐问覆盖、结果解释草稿、审计结果和现有表格/图表拼成可编辑 Markdown 报告骨架。它解决的问题是：前置工具已经能检查漏答并生成解释草稿，但人工仍要把每问的结论、证据和局限性重新整理进报告。

## 脚本路径

```text
scripts/report_section_assembler.py
```

项目脚手架会生成包装脚本：

```text
02_代码/11_report_assembler.py
```

## 输入

优先读取：

```text
06_过程记录/结果解释/result_interpretation_draft.json
06_过程记录/问题覆盖/problem_coverage.json
06_过程记录/problem_analysis.md
06_过程记录/一致性检查/auto_report_audit.json
06_过程记录/质量门禁/quality_gate_plus.json
03_结果表格/*
04_图表/*
```

如果结果解释草稿存在，脚本以其逐问信息为主；否则回退到问题覆盖追踪或 `problem_analysis.md` 中的小问拆解。

## 输出

```text
05_报告定稿/report_draft.md
06_过程记录/报告拼装/report_section_assembly.json
06_过程记录/报告拼装/report_section_assembly.md
```

`report_section_assembly.json` 同时记录：

```text
raw_data_files      # 00_题目与资料/、01_原始数据/ 下的原始附件/数据
raw_data_refs       # problem_analysis.md 中被识别为原始数据引用的文件
```

每个小问固定拼出五段：

1. 直接结论；
2. 模型与方法；
3. 证据表；
4. 图表解释；
5. 敏感性、鲁棒性与局限性。

其中“直接结论”和“模型与方法”默认保留 `待编辑`，避免脚本把草稿包装成终稿结论。

## 标准用法

在项目根目录：

```bash
python 02_代码/11_report_assembler.py
```

或直接调用技能脚本：

```bash
python ~/.hermes/skills/data-science/mathematical-modeling-agent/scripts/report_section_assembler.py .
```

指定标题和输出文件名：

```bash
python 02_代码/11_report_assembler.py --title "某某问题数学建模报告" --report-name report_draft.md
```

严格模式：

```bash
python 02_代码/11_report_assembler.py --strict
```

严格模式下，如果存在未匹配到表格/图表的小问或全局风险，返回非零退出。

## Pipeline 集成

`modeling_pipeline.py` 默认在结果解释后运行：

```text
problem_coverage
→ result_interpretation
→ report_assembly
```

新增参数：

```bash
--skip-report-assembly
--strict-report-assembly
--report-title "数学建模报告"
--report-draft-name report_draft.md
```

Pipeline 摘要会显示：

```text
报告骨架拼装：questions=N ready=R partial=P weak=W warn=X fail=Y
```

## 判定口径

- `ready`：该小问同时匹配到结果表和图表；
- `partial`：只匹配到表格或图表之一；
- `weak`：表格和图表均未匹配到；
- `fail`：无法抽取任何小问。

## 原始数据标记

报告拼装器会读取 `problem_analysis.md` 和项目内原始数据目录：

```text
00_题目与资料/
01_原始数据/
```

如果问题重述/数据清单中出现类似：

```text
Wimbledon_featured_matches.csv
data_dictionary.csv
01_原始数据/*.csv
```

生成的 `report_draft.md` 会把它们写入“原始数据引用（非结果表证据）”小节，并标注：

```text
原始数据引用，非 03_结果表格/ 的结果证据表
```

目的：避免报告一致性审计把题面附件/原始数据文件误判为缺失的结果表。真正支撑结论的文件仍必须放在 `03_结果表格/` 并在各小问“证据表”中引用。

脚本生成的是“证据优先的可编辑骨架”，不是终稿。正式提交前必须：

- 把所有 `待编辑` 改成具体内容；
- 每个直接结论都能回指结果表或图表；
- 对非 ready 小问补证据或说明无需证据；
- 重新运行 `audit_report_consistency.py`、`problem_coverage_tracker.py` 和 pipeline。

## 命名建议

为了让拼装器准确归属证据，结果表和图表建议按小问命名：

```text
03_结果表格/q1_model_results.csv
03_结果表格/q2_forecast_results.csv
03_结果表格/q3_sensitivity_results.csv
04_图表/q1_score_distribution.png
04_图表/q2_forecast_curve.png
04_图表/q3_sensitivity_bar.png
```

如果表格中有 `qid/question/问题/小问` 等列，前置 `result_interpretation_helper.py` 会更容易把表格绑定到小问。
