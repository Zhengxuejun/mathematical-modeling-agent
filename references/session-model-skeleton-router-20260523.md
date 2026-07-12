# 会话沉淀：题型路由后的模型骨架生成器（2026-05-23）

## 背景

用户连续要求“继续优化”，目标不是专项打穿某一道历史题，而是让通用数学建模智能体在正式比赛中更接近“能打、能获奖”。此前已补齐：

1. `competition_readiness_gate.py`：区分 workflow_ready / model_ready / competition_ready；
2. `competition_evidence_builder.py`：自动汇总模型、checker、求解器、仿真、敏感性、论文资产证据。

本轮发现的能力缺口是：质量门禁和证据汇总偏后验，缺少比赛开局阶段的“题型 → 模型骨架 → checker/验证资产”生产层起点。

## 已落地组件

新增：

```text
scripts/model_skeleton_router.py
references/model-skeleton-router.md
```

脚手架新增包装脚本：

```text
02_代码/15_model_skeleton.py
```

Pipeline 新增步骤：

```text
data_audit → model_skeleton → quality_gate → ...
```

早期模式：

```bash
python 02_代码/08_pipeline.py --skeleton-only --write-model-skeleton-code
```

该模式只跑早期必要步骤，避免 S1 阶段还没有结果表和报告时被终稿门禁误杀。

## 功能口径

`model_skeleton_router.py` 读取：

```text
06_过程记录/problem_analysis.md
```

自动识别题型：

- optimization：优化/资源配置；
- prediction：预测/回归/时间序列；
- evaluation：综合评价/排序；
- simulation：仿真/随机情景；
- network_routing：路径/网络/物流；
- statistics：统计检验/因果解释。

输出：

```text
06_过程记录/model_skeleton/model_skeleton.json
06_过程记录/model_skeleton/model_skeleton.md
```

加 `--write-code` 时输出 starter code：

```text
02_代码/generated_skeleton/model_main_skeleton.py
02_代码/generated_skeleton/check_constraints_skeleton.py
02_代码/generated_skeleton/sensitivity_skeleton.py
```

## 重要边界

- `model_skeleton` 通过 ≠ `model_ready`；
- skeleton 是路线起点，不是正式模型；
- starter code 不能进入最终结果口径；
- 正式比赛仍必须把骨架替换成题目特定可运行模型，运行领域 checker，生成 baseline/主模型/敏感性或风险分析对比表，再通过 `competition_evidence` 与 `competition_readiness`。

## 已验证

测试项目：

```text
~/test/model_skeleton_test_20260523_134306
```

测试 problem_analysis 同时包含物流路径优化、Monte Carlo 风险仿真、综合评价排序。

运行：

```bash
python 02_代码/08_pipeline.py --skeleton-only --write-model-skeleton-code
```

结果：

- Pipeline `recommended_status=completed`；
- `model_skeleton` pass；
- 主识别题型：`optimization`；
- 置信度：`high`；
- 识别路线数：5；
- 识别到 optimization / simulation / network_routing / evaluation / prediction。

## 后续优先级

下一刀优先做 `domain_checker` 模板库，让模型骨架不止输出文字建议，而能生成更具体的 checker 模板：

- 优化类：容量、覆盖、唯一性、上下界、目标复算；
- 路径类：节点访问、车辆容量、路径连通、时间窗；
- 预测类：数据泄漏、时间切分、误差指标；
- 评价类：权重和、指标方向、排序稳定性；
- 仿真类：seed、样本量、分布参数、极端情景；
- 统计类：独立性、重复测量、多重检验、残差诊断。
