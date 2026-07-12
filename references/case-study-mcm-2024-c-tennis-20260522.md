# 真实题端到端复跑案例：2024 MCM C Tennis Momentum

## 基本信息

- 题目：2024 MCM Problem C: Momentum in Tennis。
- 数据：Wimbledon 2023 Gentlemen's singles featured matches，公开镜像 CSV。
- 项目路径：`~/Documents/数学建模/2024_MCM_C_Tennis_技能复跑_20260522`。
- 目标：验证 `mathematical-modeling-agent` 的真实题端到端闭环，不作为正式竞赛终稿。

## 输入限制

- 题面 PDF 已获取。
- CSV 数据 7284 行、46 列、31 场比赛。
- 官方字段字典和样例原文件缺失；本次字段解释依赖题面示例与 CSV 表头。
- 数据来自公开镜像，不应在正式结论中说成“本次直接从 COMAP 官方附件下载”。

## 采用模型

1. Q1：发球校正 EWMA momentum。
   - `serve_adjusted_point_value = I(p1 wins) - E[I(p1 wins)|server]`
   - `momentum_t = (1-alpha) momentum_{t-1} + alpha * serve_adjusted_point_value_t`
2. Q2：置换检验，比较真实最长同向运行长度与随机置换基准。
3. Q3：无 sklearn 依赖的相关性评分模型，按比赛 holdout 预测 `swing_next`。
4. Q4：跨 31 场比赛输出 per-match 指标，并对 EWMA alpha 做敏感性。
5. Q5：把建模结果转化为教练建议草稿。

## 关键结果

- 数据审计：7284 行、46 列、31 场比赛、2169 个缺失单元格、0 个完全重复行。
- Q2 示例决赛：observed_longest_run=7，perm_mean_longest_run=8.613，permutation_p_value=0.9221，当前定义下不能拒绝随机假设。
- Q3 swing 预测：test_points=1848，swing_rate_test=0.2376，accuracy=0.6845，AUC=0.8252。
- Q4 alpha 敏感性：alpha=0.10/0.18/0.30 对应 mean_abs_momentum=0.0923/0.1229/0.1631。

## Pipeline 验证结果

最终状态：

```text
Recommended status: completed
Highest contiguous state: S8
```

审计摘要：

```text
报告一致性审计：pass=8 warn=1 fail=0
增强质量门禁：pass=18 warn=1 fail=0
问题覆盖追踪：questions=5 missing=0 weak_assets=1 warn=2 fail=0
结果解释草稿：questions=5 without_tables=5 warn=5 fail=0
报告骨架拼装：questions=5 ready=0 partial=3 weak=2 warn=6 fail=0
修复建议：delivery_readiness=needs_review advice=9 warn=9 fail=0
```

## 暴露的技能缺陷

1. `problem_coverage_tracker.py` 需要支持 `### Q1 ...` 等常见竞赛标题格式。
2. 报告一致性审计需要区分“原始数据 CSV 引用”和“结果表 CSV 引用”。
3. 模板应轻依赖优先，避免环境缺 sklearn 时真实链路中断。
4. 结果解释器需要从文件名和章节关键词软映射表格到小问。
5. 报告拼装器应为 raw input 文件名加语境标记，避免被表格审计误杀。

## 后续维护建议

优先实现：

1. 小问抽取增强。
2. 原始附件/结果表引用语境区分。

这两项是本次真实题复跑中最明确、收益最高的脚本级修复点。
