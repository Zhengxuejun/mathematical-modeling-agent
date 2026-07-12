# 问题小问覆盖追踪器 problem_coverage_tracker

`problem_coverage_tracker.py` 用于防止数学建模报告出现“模型、图表和结果很多，但漏答某一小问”的提交风险。

## 脚本路径

```text
scripts/problem_coverage_tracker.py
```

项目脚手架会生成包装脚本：

```text
02_代码/09_problem_coverage.py
```

## 输入与输出

输入：

```text
06_过程记录/problem_analysis.md
05_报告定稿/*.md|*.tex|*.docx
03_结果表格/*.csv|*.json|*.xlsx|*.xls
04_图表/*.png|*.jpg|*.jpeg|*.svg|*.pdf
```

输出：

```text
06_过程记录/问题覆盖/problem_coverage.json
06_过程记录/问题覆盖/problem_coverage.md
```

## 标准用法

在项目根目录：

```bash
python 02_代码/09_problem_coverage.py
```

或直接调用技能脚本：

```bash
python ~/.hermes/skills/data-science/mathematical-modeling-agent/scripts/problem_coverage_tracker.py .
```

严格模式：

```bash
python 02_代码/09_problem_coverage.py --strict
```

要求每问至少有一个表格/图表侧证据，未满足则 warning；严格模式下 warning 会导致非零退出：

```bash
python 02_代码/09_problem_coverage.py --strict --min-asset-hits 1
```

## 小问抽取规范

推荐在 `problem_analysis.md` 的 `## 小问拆解` 下用以下格式记录：

```markdown
## 小问拆解

- 问题1：建立评价指标体系，判断各对象综合得分。
- 问题2：构建预测模型，预测未来三期关键指标。
- 问题3：进行敏感性分析，并提出优化建议。
```

也支持常见 Markdown 标题/英文题号：

```markdown
### Q1 Momentum definition and visualization
### Q2: Test whether swings are random
## Problem 3 Robustness analysis
```

也支持：

```markdown
1. 数据预处理与异常识别
2. 主模型建立与结果解释
3. 鲁棒性验证
```

但为了稳定追踪，正式项目优先使用“问题1/问题2/问题3”。

## 判定口径

对每个抽取到的小问，脚本会生成关键词集合，包括：

- `Q1` / `问题1` / `小问1`；
- 小问文本中的中文关键词、英文关键词、数字 token；
- 去除“问题、任务、目标、模型、结果”等泛词。

然后检查：

| 检查对象 | 作用 |
|---|---|
| 报告正文 | 判断该小问是否被文字回答 |
| 结果表文件名/CSV/JSON 文本 | 判断是否有结果证据 |
| 图表文件名 | 判断是否有图形证据 |

状态含义：

- `pass`：报告覆盖该小问，且若设置 `--min-asset-hits`，侧证据满足要求。
- `warn`：报告覆盖了，但表格/图表侧证据不足。
- `fail`：报告未覆盖该小问，或未能抽取到小问清单。

## 与 Pipeline 的关系

`modeling_pipeline.py` 已接入本脚本，链路为：

```text
data_audit
→ quality_gate
→ report_audit
→ state_update_pre_finalize
→ finalize
→ state_update_final
→ quality_gate_plus
→ problem_coverage
```

Pipeline 参数：

```bash
python 02_代码/08_pipeline.py --strict --zip
python 02_代码/08_pipeline.py --strict --zip --coverage-min-asset-hits 1
python 02_代码/08_pipeline.py --skip-coverage
```

Pipeline 摘要会写入：

```text
问题覆盖追踪：questions=N missing=M weak_assets=K warn=W fail=F
```

## 注意事项

1. 本脚本是启发式覆盖检查，不证明答案正确。
2. PDF 报告默认不做深度文本解析；正式自动审计优先保留 Markdown/TeX/DOCX 源文件。
3. 侧证据主要靠文件名和 CSV/JSON 文本匹配，因此建议结果表/图表命名包含小问编号，例如：
   - `q1_evaluation_results.csv`
   - `q2_forecast_results.csv`
   - `q3_sensitivity_results.csv`
4. 若报告确实合并回答多个小问，建议在小节标题中显式写“问题1-2”。
5. 漏答小问应优先补报告和结果证据，而不是降低门禁。
