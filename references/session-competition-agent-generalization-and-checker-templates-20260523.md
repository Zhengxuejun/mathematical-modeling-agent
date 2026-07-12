# 会话沉淀：通用数学建模智能体冲奖级优化（2026-05-23）

## 背景

用户连续要求“继续，目标是能真正打比赛，并且能获奖”。关键纠偏是：优化对象不是专项打穿某一道历史题，而是提升通用数学建模智能体在正式比赛中的能力。历史题只作为测试 fixture，用来暴露可复用缺陷。

## 本轮形成的通用能力链

围绕“流程跑通 ≠ 模型能打 ≠ 论文能获奖”，本轮把数学建模智能体从后验流程闭环，推进到更完整的比赛质量控制链：

```text
题目解析
→ 题型路由
→ 模型骨架
→ 领域 checker 模板
→ 正式题目模型
→ 正式 checker issue_count=0
→ competition_evidence
→ competition_readiness
→ 报告/提交包
```

## 新增/强化的组件口径

### 1. model_skeleton_router

脚本：`scripts/model_skeleton_router.py`

作用：读取 `06_过程记录/problem_analysis.md`，识别题型并生成：

```text
06_过程记录/model_skeleton/model_skeleton.json
06_过程记录/model_skeleton/model_skeleton.md
```

可选生成 starter code：

```text
02_代码/generated_skeleton/model_main_skeleton.py
02_代码/generated_skeleton/check_constraints_skeleton.py
02_代码/generated_skeleton/sensitivity_skeleton.py
```

支持题型：优化、预测、评价、仿真、路径/网络、统计检验等。

关键口径：`model_skeleton` 只是路线起点，不等于 `model_ready`。正式比赛必须把骨架替换为题目特定可运行模型。

### 2. domain_checker_template_builder

脚本：`scripts/domain_checker_template_builder.py`

作用：读取 `model_skeleton.json`，为排名靠前的题型生成 checker starter：

```text
06_过程记录/领域checker/domain_checker_templates.json
06_过程记录/领域checker/domain_checker_templates.md
02_代码/generated_checkers/check_<type>.py
```

覆盖检查项包括：

- 优化类：容量/预算/面积、覆盖/唯一性、变量上下界、目标函数复算、求解状态；
- 路径类：节点访问、路径连通、车辆容量、时间窗、距离/成本复算；
- 预测类：时间/主体切分、泄漏、baseline、误差指标、残差诊断；
- 评价类：指标方向、标准化、权重和、排序复算、稳定性；
- 仿真类：seed、分布参数、情景数、风险指标、极端情景可行性；
- 统计类：独立性/重复测量、检验前提、多重检验、效应量与置信区间、稳健模型。

关键口径：生成 checker 模板不等于正式 checker 证据。模板默认含 TODO/warn；只有替换为读取正式结果表/参数表/路线表/预测表/评价矩阵的硬检查，运行后 `issue_count=0`，才能作为 `competition_evidence.domain_checker` 的 `model_ready` 证据。

### 3. skeleton-only early pipeline

Pipeline 新增早期模式：

```bash
python 02_代码/08_pipeline.py --skeleton-only --write-model-skeleton-code
```

用途：比赛刚读完题、处于 S1/S2 早期时，只跑早期步骤，避免没有结果表/报告时被终稿门禁误杀。

早期顺序：

```text
data_audit → model_skeleton → domain_checker_templates → quality_gate
```

## 设计原则

1. **历史题作为 fixture，不作为硬编码目标**：不能为了 2024C、MCM C 等单题写死逻辑；从真实题暴露的失败模式中抽象通用门禁、模板和 checker。
2. **质量控制先于高级模型堆砌**：获奖级能力来自“路线正确、约束可查、结果可复算、论文能解释”，不是模型名多。
3. **分层表达状态**：最终回复应区分 `workflow_ready`、`model_ready`、`competition_ready`，不能把 S8/completed 说成可获奖。
4. **模板不是证据**：任何 skeleton/template/checker starter 都只能是生产起点，不能作为正式模型或正式约束验证证据。
5. **正式比赛下一步优先 evidence 联动**：后续应让 `competition_evidence_builder.py` 区分 `template_checker_only`、`implemented_checker_warn`、`implemented_checker_pass`。

## 验证 fixture

测试项目：

```text
~/test/model_skeleton_test_20260523_134306
```

输入为物流路径优化 + Monte Carlo 风险仿真 + 综合评价排序的小问解析。早期 pipeline 验证结果：

```text
模型骨架路由：primary=optimization confidence=high routes=5
领域checker模板：types=optimization,simulation,network_routing files=3
```

这证明路由器能识别多题型组合，并为前三类生成 checker 模板。
