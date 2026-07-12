# 会话沉淀：结果解释生成器与连续优化纪律（2026-05-22）

本文件记录本轮对 `mathematical-modeling-agent` 的可复用工程化经验，避免后续只停留在规划层。

## 本轮新增组件

### 1. 问题小问覆盖追踪器

已实现：

```text
scripts/problem_coverage_tracker.py
references/problem-coverage-tracker.md
```

核心作用：

- 从 `06_过程记录/problem_analysis.md` 的“小问拆解/问题拆解/任务清单/子任务”抽取问题清单；
- 检查 `05_报告定稿/`、`03_结果表格/`、`04_图表/` 是否逐问覆盖；
- 输出 `06_过程记录/问题覆盖/problem_coverage.md/json`；
- 支持 `--strict` 和 `--min-asset-hits`，用于把“报告漏答某问”变成可机器拦截的失败。

实践口径：正式项目中，`problem_analysis.md` 应优先使用“问题1/问题2/问题3”这类稳定编号；结果表和图表文件名建议包含 `q1/q2/q3` 或 `问题1/问题2/问题3`，提高自动匹配准确率。

### 2. 模型结果解释生成器

已实现：

```text
scripts/result_interpretation_helper.py
references/result-interpretation-helper.md
```

核心作用：

- 读取 `problem_coverage.json`、`problem_analysis.md`、CSV/JSON 结果表和图表文件；
- 为每问匹配结果表、图表和关键数值；
- 生成 `06_过程记录/结果解释/result_interpretation_draft.md/json`；
- 输出保守解释草稿，不编造结论；
- 若某问缺少结果表或审计存在 fail，会显式给出风险提示。

实践口径：该脚本是“报告写作辅助”，不是最终报告生成器。它的价值是把真实结果证据组织成“直接结论—关键值—图表证据—风险提示”的材料，供后续人工/智能体改写。

## Pipeline 集成后的完整链路

当前 `modeling_pipeline.py` 的闭环链路应保持为：

```text
data_audit
→ quality_gate
→ report_audit
→ state_update_pre_finalize
→ finalize
→ state_update_final
→ quality_gate_plus
→ problem_coverage
→ result_interpretation
```

Pipeline 摘要应包含：

```text
报告一致性审计 pass/warn/fail
增强质量门禁 pass/warn/fail
问题覆盖追踪 questions/missing/weak_assets
结果解释草稿 questions/without_tables/warn/fail
最终打包检查 warn/fail
recommended_status
highest_contiguous_state
```

## 新项目脚手架应包含

`create_modeling_project.py` 创建新项目时，应包含：

```text
06_过程记录/问题覆盖/
06_过程记录/结果解释/
02_代码/09_problem_coverage.py
02_代码/10_result_interpretation.py
```

并在 `project_meta.json` 中记录：

```json
"problem_coverage_tracker": "02_代码/09_problem_coverage.py",
"result_interpretation_helper": "02_代码/10_result_interpretation.py"
```

## 验证纪律

新增此类工程组件后，必须至少验证：

1. `python -m py_compile` 通过；
2. 单组件正例通过；
3. 单组件风险/负例能暴露问题；
4. Pipeline 集成正例通过；
5. 技能目录无残留 `__pycache__`；
6. Python 缓存移动到 macOS 回收站 `~/.Trash/`，不得硬删除。

本轮已验证的正例口径：

```text
recommended_status = completed
highest_contiguous_state = S8
problem_coverage.missing_questions = 0
result_interpretation.fail = 0
```

## 下一步优先级

若用户继续要求“继续优化”，下一步优先做：

```text
scripts/report_section_assembler.py
```

目标：读取 `problem_analysis.md`、`result_interpretation_draft.json`、`auto_report_audit.json` 和质量门禁结果，拼装可编辑 Markdown 报告骨架。每问至少包含：

```text
直接结论
证据表
图表解释
局限性/风险提示
```

注意：报告拼装器也应坚持“证据优先”，不能把解释草稿包装成已验证最终结论。
