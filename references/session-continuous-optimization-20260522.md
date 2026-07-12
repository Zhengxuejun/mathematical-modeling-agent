# 连续优化会话沉淀：数学建模智能体工程闭环

本记录沉淀本轮对 `mathematical-modeling-agent` 的连续优化模式，供未来维护该技能时复用。它不是某个建模题的流水账，而是“如何把方法论技能推进为可运行工程闭环”的经验。

## 已落地组件序列

```text
项目脚手架
→ 最终提交包生成
→ 报告-结果一致性自动审计
→ S0-S8 状态机自动推进
→ modeling_pipeline 总控运行器
→ quality_gate_plus 增强质量门禁
```

## 关键设计原则

1. **连续优化必须落地组件**：用户说“继续优化”时，不停留在建议层；每轮选一个最高杠杆组件，写脚本/引用文档，接入 SKILL.md，并做最小闭环验证。
2. **Pipeline 负责串流程，增强门禁负责判实质**：`modeling_pipeline.py` 统一调度；`quality_gate_plus.py` 检查结果表可读非空、baseline/core/sensitivity、报告逐问痕迹、图表/表格引用、状态与 meta 一致性。
3. **状态必须由证据推导**：S0-S8 不靠口头判断；由真实产物路径与文件内容推断，且按连续完成状态计算。
4. **严格模式要能暴露风险**：报告未引用结果表、报告数字无法匹配结果表、质量门禁 warning，在 `--strict` 下应失败，而不是假通过。
5. **验证包含正负例**：新增脚本至少跑 `py_compile`、正例闭环、负例/风险信号触发；只跑正例不足以证明门禁有效。
6. **文件卫生**：测试项目放 `~/test/`；编译产生的 `__pycache__` 移动到 `~/.Trash/`，不硬删除。

## 当前推荐维护循环

```text
读取 SKILL.md 与 continuous-optimization-notes.md
→ 选择下一组件
→ 写 scripts/ 或 references/
→ 更新 SKILL.md 指针
→ 接入 create_modeling_project.py 或 modeling_pipeline.py
→ py_compile
→ 最小项目正例验证
→ 至少一个风险/负例验证
→ 清理 __pycache__ 到 ~/.Trash
→ 更新 continuous-optimization-notes.md 的已实现与下一步
```

## 下一步优先方向

优先实现：

```text
scripts/problem_coverage_tracker.py
```

目标：从 `problem_analysis.md` 抽取题目小问，检查报告、结果表、图表和最终提交包是否逐问覆盖，防止“模型和图表很多，但漏答某一问”。
