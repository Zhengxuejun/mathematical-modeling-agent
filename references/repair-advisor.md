# 修复建议器 repair_advisor

`repair_advisor.py` 用于把分散在 pipeline、质量门禁、报告一致性审计、问题覆盖、结果解释、报告拼装和提交包检查中的 fail/warn 汇总为一份优先级修复清单。它回答三个问题：

1. 当前能不能交？
2. 还差什么？
3. 先修哪里？

## 脚本路径

```text
scripts/repair_advisor.py
```

项目脚手架会生成包装脚本：

```text
02_代码/12_repair_advisor.py
```

## 输入

```text
06_过程记录/pipeline/pipeline_run_summary.json
06_过程记录/质量门禁/quality_gate_plus.json
06_过程记录/问题覆盖/problem_coverage.json
06_过程记录/结果解释/result_interpretation_draft.json
06_过程记录/报告拼装/report_section_assembly.json
06_过程记录/一致性检查/auto_report_audit.json
07_提交包/submission_manifest.json
```

输入文件不存在时不会崩溃，会在证据不足时给出 `unknown` 或补跑 pipeline 的建议。

## 输出

```text
06_过程记录/修复建议/repair_advice.json
06_过程记录/修复建议/repair_advice.md
```

输出包含：

- `delivery_readiness`：`ready` / `needs_review` / `blocked` / `unknown`；
- pipeline 状态和最高连续状态；
- fail/warn/info 数量；
- 按优先级排序的修复清单；
- 每项的来源、问题、建议动作和证据。

## 判定口径

- `blocked`：存在 fail 级修复项，不建议提交；
- `needs_review`：无 fail，但存在 warn，正式提交前应确认或消除；
- `ready`：无 fail/warn，且 pipeline `completed`、状态机到 `S8`；
- `unknown`：缺少完整 pipeline/S8 证据，无法判断。

## 标准用法

在项目根目录：

```bash
python 02_代码/12_repair_advisor.py
```

或直接调用技能脚本：

```bash
python ~/.hermes/skills/data-science/mathematical-modeling-agent/scripts/repair_advisor.py .
```

严格模式：

```bash
python 02_代码/12_repair_advisor.py --strict
```

严格模式下，只要 `delivery_readiness != ready` 就返回非零退出。

## Pipeline 集成

`modeling_pipeline.py` 默认最后运行：

```text
problem_coverage
→ result_interpretation
→ report_assembly
→ repair_advisor
```

新增参数：

```bash
--skip-repair-advisor
--strict-repair-advisor
```

Pipeline 摘要会显示：

```text
修复建议：delivery_readiness=ready advice=0 warn=0 fail=0
```

## 使用建议

正式提交前推荐：

```bash
python 02_代码/08_pipeline.py --zip --coverage-min-asset-hits 1
python 02_代码/12_repair_advisor.py
```

如果 `repair_advice.md` 显示 `blocked`，先按优先级从小到大修复 fail 项；不要只改最终报告文字绕过检查。修复后重新运行 pipeline，直到至少达到 `needs_review`，最好达到 `ready`。
