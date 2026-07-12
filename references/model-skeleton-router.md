# 题型路由后的模型骨架生成器

## 目标

`model_skeleton_router.py` 用于把 `problem_analysis.md` 中的题目解析转成比赛级建模骨架，解决“质量门禁能检查，但早期不知道该搭什么模型”的问题。

它不是自动生成最终答案，也不会把 skeleton 伪装成正式模型。它的职责是：

1. 识别题型：优化、预测、评价、仿真、路径/网络、统计检验等；
2. 输出变量/参数、模型核心、领域 checker、验证资产建议；
3. 可选生成 starter code，迫使项目一开始就有 `model → checker → sensitivity` 的结构；
4. 为后续 `competition_evidence` 和 `competition_readiness` 提供更明确的模型证据来源。

## 输入

默认读取：

```text
06_过程记录/problem_analysis.md
```

因此它依赖 S1 题目解析质量。若 `problem_analysis.md` 只有空模板，路由会低置信或 unknown。

## 输出

```text
06_过程记录/model_skeleton/model_skeleton.json
06_过程记录/model_skeleton/model_skeleton.md
```

加 `--write-code` 时还会生成：

```text
02_代码/generated_skeleton/model_main_skeleton.py
02_代码/generated_skeleton/check_constraints_skeleton.py
02_代码/generated_skeleton/sensitivity_skeleton.py
```

这些代码是 starter，不是正式模型。正式比赛中应把它们迁移/改写为题目特定的 `03_model_main.py`、checker 和敏感性分析脚本。

## 命令

```bash
python ~/.hermes/skills/data-science/mathematical-modeling-agent/scripts/model_skeleton_router.py <project> --write-code
# 或在项目内跑早期 pipeline：
python 02_代码/08_pipeline.py --skeleton-only --write-model-skeleton-code
```

严格模式：

```bash
python ~/.hermes/skills/data-science/mathematical-modeling-agent/scripts/model_skeleton_router.py <project> --strict
```

若题型 unknown 或低置信，`--strict` 返回非零退出码。

## Pipeline 位置

推荐在以下步骤之后、质量门禁之前运行：

```text
data_audit → model_skeleton → quality_gate → ...
```

原因：

- 先有数据审计，能让 problem_analysis 更容易补齐字段与目标；
- 再做模型骨架，后续质量门禁和竞赛证据才能检查“是否从骨架升级为正式模型”；
- 不应等到 report_assembly 后才发现模型路线错了。

## 比赛使用口径

- `model_skeleton` 通过 ≠ `model_ready`；
- skeleton 只是“路线正确的起点”；
- 只有替换 placeholder、运行题目特定模型、领域 checker `issue_count=0`、完成对比/敏感/风险分析后，才可能进入 `competition_ready`。
