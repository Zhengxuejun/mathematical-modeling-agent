# 增强质量门禁 quality_gate_plus

`quality_gate_plus.py` 是 `mathematical-modeling-agent` 的增强质量门禁。它补足轻量 `02_代码/06_quality_gate.py` 只检查文件存在的不足，重点检查产物是否有最低实质内容。

## 1. 脚本路径

```text
scripts/quality_gate_plus.py
```

输出：

```text
06_过程记录/质量门禁/quality_gate_plus.json
06_过程记录/质量门禁/quality_gate_plus.md
```

## 2. 使用方式

普通模式：

```bash
python ~/.hermes/skills/data-science/mathematical-modeling-agent/scripts/quality_gate_plus.py .
```

严格模式：

```bash
python ~/.hermes/skills/data-science/mathematical-modeling-agent/scripts/quality_gate_plus.py . --strict
```

要求最终提交包也完整：

```bash
python ~/.hermes/skills/data-science/mathematical-modeling-agent/scripts/quality_gate_plus.py . --expect-final
```

Pipeline 中默认在 finalize 和最终 state update 后运行：

```text
quality_gate_plus --expect-final
```

若 Pipeline 使用 `--strict`，则增强质量门禁也使用严格模式。

## 3. 检查内容

| 检查项 | 说明 |
|---|---|
| standard_directories | 标准 00-07 目录是否存在 |
| materials_or_raw_data | 题面或原始数据是否存在 |
| problem_analysis_substantive | `problem_analysis.md` 是否有实质内容 |
| result_tables_readable | CSV/JSON/XLSX 结果表是否可读 |
| result_tables_nonempty | 结果表是否非空 |
| baseline_result_exists | baseline/基线结果是否存在 |
| core_model_result_exists | 主模型/核心模型结果是否存在 |
| sensitivity_result_exists | 敏感性/鲁棒性结果是否存在 |
| figures_exist | 图表是否存在 |
| figures_not_tiny | 图表文件是否疑似空/占位 |
| report_exists | 报告文件是否存在 |
| report_text_substantive | Markdown/LaTeX/DOCX 文本是否有实质内容 |
| report_answers_problem_sections | 报告是否出现逐问回答痕迹 |
| report_references_figures | 有图表时报告是否引用图 |
| report_references_tables | 有结果表时报告是否引用表 |
| auto_report_audit_clean | 自动报告一致性审计是否无 fail/warn |
| state_meta_consistent | PROJECT_STATE 与 project_meta 状态是否一致 |
| final_package_complete | README_submit/SHA256SUMS/manifest 是否齐全 |
| pipeline_summary_exists | Pipeline 摘要是否存在 |

## 4. 判定口径

- `fail`：关键闭环证据缺失或结果表不可读/为空。
- `warn`：可能需要人工检查，例如报告文本太短、没有逐问痕迹、图表疑似占位。
- `pass`：满足最低工程证据。

严格模式下：

```text
fail 或 warn 均返回非零
```

普通模式下：

```text
只有 fail 返回非零
```

## 5. 注意事项

- 它不证明模型数学上正确，只证明工程交付证据有最低完整性。
- PDF 不做文本深度解析，因此 PDF-only 报告可能出现文本不足 warning；终稿建议保留 Markdown/LaTeX/DOCX 源文件用于审计。
- “报告是否回答每个小问”是启发式检查，不能替代人工/智能体精读。
- 图表小文件检查只用于发现明显占位文件，不能判断图表内容质量。
