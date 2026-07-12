# 会话沉淀：问题小问覆盖追踪器优化（2026-05-22）

本记录沉淀 `mathematical-modeling-agent` 连续优化中新增 `problem_coverage_tracker.py` 的设计与验证经验。它不是一次任务流水账，而是后续维护数学建模工程闭环时应继承的可复用模式。

## 背景信号

用户连续要求“继续优化”时，当前技能的下一优先级是从“整体项目可提交”推进到“每个题目小问都被明确回答”。此前 `quality_gate_plus.py` 只能检查报告中是否有逐问痕迹，不能定位具体漏答了哪一问。

## 新增组件

```text
scripts/problem_coverage_tracker.py
references/problem-coverage-tracker.md
02_代码/09_problem_coverage.py  # 新项目脚手架生成的包装脚本
06_过程记录/问题覆盖/            # 新项目脚手架生成的输出目录
```

## 核心方法

1. 从 `06_过程记录/problem_analysis.md` 的 `小问拆解 / 问题拆解 / 任务清单 / 子任务` 等章节抽取小问。
2. 推荐正式项目使用稳定格式：

   ```markdown
   ## 小问拆解

   - 问题1：建立评价指标体系，计算对象综合得分。
   - 问题2：构建预测模型，预测未来三期需求。
   - 问题3：进行敏感性分析，并提出优化建议。
   ```

3. 为每个小问构造关键词：`Q1 / 问题1 / 小问1` 加小问文本中的高信号中文、英文、数字 token。
4. 逐问检查：
   - 报告文本命中：`05_报告定稿/*.md|*.tex|*.docx`；
   - 结果表证据：`03_结果表格/*.csv|*.json|*.xlsx|*.xls` 的文件名和可读文本；
   - 图表证据：`04_图表/*` 文件名。
5. 输出机器可读 JSON 与人类可读 Markdown：

   ```text
   06_过程记录/问题覆盖/problem_coverage.json
   06_过程记录/问题覆盖/problem_coverage.md
   ```

## 判定口径

- `fail`：无法抽取小问，或某小问在报告中没有覆盖。
- `warn`：报告覆盖了，但设置 `--min-asset-hits` 后结果表/图表侧证据不足。
- `pass`：报告覆盖，且侧证据满足要求。

常用命令：

```bash
python 02_代码/09_problem_coverage.py
python 02_代码/09_problem_coverage.py --strict
python 02_代码/09_problem_coverage.py --strict --min-asset-hits 1
```

## Pipeline 集成

`modeling_pipeline.py` 现在应把覆盖追踪作为最终检查链路的一环：

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

新增 Pipeline 参数：

```bash
--skip-coverage
--coverage-min-asset-hits 1
```

Pipeline 摘要应包含：

```text
问题覆盖追踪：questions=N missing=M weak_assets=K warn=W fail=F
```

## 验证模式

最小正例应包含：

- `problem_analysis.md` 中 3 个小问；
- 报告中逐问出现问题1/问题2/问题3；
- 每问至少一个表格或图表侧证据；
- `problem_coverage_tracker.py --strict --min-asset-hits 1` 退出码为 0。

负例验证应删除报告中某一问，例如“问题2”，再运行严格模式，预期退出码非 0，并在 `problem_coverage.json/md` 中显示对应小问缺失。

## 文件卫生规则

- 新增脚本必须执行 `python -m py_compile`。
- 产生的 `__pycache__` 必须移动到 macOS 回收站 `~/.Trash/`，不硬删除。
- 测试项目放 `~/test/`。
- 验证后确认技能目录无残留 `__pycache__`。

## 后续优化方向

下一阶段优先做：

```text
scripts/result_interpretation_helper.py
```

目标：读取核心结果表、敏感性分析表和覆盖追踪结果，为每个小问生成结论草稿、图表解释草稿和风险提示，把“检查漏答”推进到“辅助补全报告解释”。
