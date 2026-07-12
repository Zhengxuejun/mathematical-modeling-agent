# 模型结果解释生成器 result_interpretation_helper

`result_interpretation_helper.py` 用于把结果表、图表和问题覆盖追踪结果转化为逐问解释草稿。它解决的问题是：自动门禁能发现“漏答/缺证据”，但报告写作仍容易缺少对核心数值、图表和敏感性结果的解释。

## 脚本路径

```text
scripts/result_interpretation_helper.py
```

项目脚手架会生成包装脚本：

```text
02_代码/10_result_interpretation.py
```

## 输入

脚本会读取：

```text
06_过程记录/问题覆盖/problem_coverage.json
06_过程记录/problem_analysis.md
03_结果表格/*.csv|*.json
04_图表/*
06_过程记录/一致性检查/auto_report_audit.json
06_过程记录/质量门禁/quality_gate_plus.json
```

目前主要深读 CSV/JSON；XLSX 可在后续扩展。图表侧主要使用文件名匹配小问。匹配逻辑不只依赖 `q1/q2` 编号，也会读取表名、列名、前几行文本和关键词别名，例如 momentum/randomness/swing/sensitivity 等真实建模题常见词，以支持“一张表或无 Q 编号文件覆盖某一问”的场景。

## 输出

```text
06_过程记录/结果解释/result_interpretation_draft.json
06_过程记录/结果解释/result_interpretation_draft.md
```

输出内容包括：

- 每问匹配到的结果表；
- 每问匹配到的图表；
- 从数值列中提取的关键值、min、max；
- 可直接进入报告初稿的保守解释段落；
- 缺少表格/图表证据、覆盖追踪 warning、一致性审计 fail 等风险提示。

## 标准用法

在项目根目录：

```bash
python 02_代码/10_result_interpretation.py
```

或直接调用技能脚本：

```bash
python ~/.hermes/skills/data-science/mathematical-modeling-agent/scripts/result_interpretation_helper.py .
```

严格模式：

```bash
python 02_代码/10_result_interpretation.py --strict
```

严格模式下，如果存在未匹配到结果表的小问、全局审计风险或其他 warning，会返回非零退出。

## Pipeline 集成

`modeling_pipeline.py` 已接入本脚本。默认在 `problem_coverage` 后运行：

```text
quality_gate_plus
→ problem_coverage
→ result_interpretation
```

Pipeline 参数：

```bash
python 02_代码/08_pipeline.py --zip
python 02_代码/08_pipeline.py --skip-interpretation
python 02_代码/08_pipeline.py --strict-interpretation
```

Pipeline 摘要会显示：

```text
结果解释草稿：questions=N without_tables=K warn=W fail=F
```

## 报告写作建议

生成的草稿不是最终结论，不能无脑粘贴。正式报告中应按以下顺序改写：

1. 先用一句话直接回答该问；
2. 再引用结果表中的核心数值；
3. 然后解释图表趋势或排序含义；
4. 最后说明敏感性、鲁棒性或局限性；
5. 若脚本提示“未匹配到结果表”，必须先补结果证据，而不是只补文字。

## 命名规范

为了提高匹配准确性，建议结果表和图表包含小问编号：

```text
q1_evaluation_results.csv
q2_forecast_results.csv
q3_sensitivity_results.csv
q1_score.png
q2_forecast.png
q3_sensitivity.png
```

也可以在结果表中加入：

```text
question,qid,问题,小问
```

等列，让脚本能直接匹配小问。
