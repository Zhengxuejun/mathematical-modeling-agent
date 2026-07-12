# 会话沉淀：修复建议器与交付 readiness（2026-05-22）

本记录沉淀本轮连续优化中 `repair_advisor.py` 的设计、验证和后续使用口径。它属于 `mathematical-modeling-agent` 的工程闭环层，不是单题经验。

## 背景

在完成以下链路后：

```text
problem_coverage_tracker
→ result_interpretation_helper
→ report_section_assembler
```

系统已经能发现漏答、生成逐问解释草稿、拼装可编辑报告骨架。但用户继续要求优化时，最有价值的下一步不再是新增检查点，而是把分散的 fail/warn 转成可执行修复建议。

## 已落地组件

```text
scripts/repair_advisor.py
references/repair-advisor.md
02_代码/12_repair_advisor.py
06_过程记录/修复建议/
```

输入聚合：

```text
06_过程记录/pipeline/pipeline_run_summary.json
06_过程记录/质量门禁/quality_gate_plus.json
06_过程记录/问题覆盖/problem_coverage.json
06_过程记录/结果解释/result_interpretation_draft.json
06_过程记录/报告拼装/report_section_assembly.json
06_过程记录/一致性检查/auto_report_audit.json
07_提交包/submission_manifest.json
```

输出：

```text
06_过程记录/修复建议/repair_advice.md
06_过程记录/修复建议/repair_advice.json
```

## readiness 口径

```text
ready         无 fail/warn，pipeline completed，状态机到 S8
needs_review  无 fail，但存在 warn，需人工确认或消除
blocked       存在 fail，不建议提交
unknown       缺少完整 pipeline/S8 证据，无法判断
```

注意：`needs_review` 不是失败。数学建模报告中图号/表号缺失、problem_analysis 偏简略等 warning 可以提醒人工终稿检查，但不应直接阻断。

## 关键实现经验

1. `repair_advisor.py` 不应成为另一个独立质量门禁；它的职责是翻译现有检查结果。
2. 先读取 pipeline failed steps，因为命令级失败优先级最高。
3. 再读取结构化 findings/checks，例如 `quality_gate_plus.findings`、`auto_report_audit.findings`、`submission_manifest.checks`。
4. 再按 counts 推导问题，例如 `missing_questions`、`drafts_without_tables`、`weak_sections`。
5. 建议动作要具体到文件/目录和复验命令，避免只说“请修复”。
6. 对 `report_referenced_tables_exist` 这类项，动作应优先解释为“修正/补齐报告引用的结果表”，不能泛化成“补充报告文件”。
7. Pipeline 集成时，需要在运行 repair_advisor 前先写一次 preliminary pipeline summary，让它能读取前面步骤状态；repair_advisor 跑完后再写最终 pipeline summary。

## 验证模式

正例：构造三问项目，补齐：

```text
problem_analysis.md
q1/q2/q3 结果表
q1/q2/q3 图表
baseline_results.csv
model_results.csv
sensitivity_results.csv
report.md
```

运行：

```bash
python scripts/modeling_pipeline.py <project> --zip --coverage-min-asset-hits 1 --entry 02_代码/03_model_main.py --skip-data-audit --skip-quality-gate
```

预期：

```text
recommended_status=completed
highest_contiguous_state=S8
repair_advice.md 生成
```

如果仍有图号/表号或题解简略 warning，`delivery_readiness=needs_review` 是合理结果。

负例：故意让报告引用不存在的：

```text
missing_table.csv
```

预期：

```text
report_audit/finalize/quality_gate_plus/repair_advisor 失败
delivery_readiness=blocked
repair_advice.md 定位 missingtable，并建议修正文件名、补表或删除引用
```

## 后续策略

到 repair_advisor 后，继续横向堆小检查器的边际收益下降。下一步应优先做真实题端到端复跑验证：用一个真实数学建模题完整跑通读题、建模、代码、图表、报告骨架、修复建议和提交包，用真实失败模式反向校准现有组件。
