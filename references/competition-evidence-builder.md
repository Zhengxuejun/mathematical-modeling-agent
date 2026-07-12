# 竞赛证据自动汇总器 / Competition Evidence Builder

`competition_evidence_builder.py` 用于自动生成：

```text
06_过程记录/competition_evidence.json
06_过程记录/competition_evidence.md
```

它服务于 `competition_readiness_gate.py`：把项目中的模型、checker、求解器、仿真、敏感性、对比、论文资产等证据汇总成机器可读文件，减少就绪度门禁只靠关键词猜测。

## 命令

```bash
python ~/.hermes/skills/data-science/mathematical-modeling-agent/scripts/competition_evidence_builder.py <project>
python ~/.hermes/skills/data-science/mathematical-modeling-agent/scripts/competition_evidence_builder.py <project> --strict
```

新项目脚手架内包装脚本：

```bash
python 02_代码/14_competition_evidence.py
```

Pipeline 中默认在 `repair_advisor` 后、`competition_readiness` 前运行。

## 自动汇总内容

- `artifact_counts`：原始材料、代码、结果表、非空表、图表、报告数量；
- `problem_specific_model`：是否检测到正式模型证据，是否仍有 placeholder/TODO/链路测试文本；
- `domain_checker`：是否检测到 checker/validate/constraint/audit 类脚本或记录，是否能提取 `issue_count`；
- `official_templates_filled`：是否存在 `result*`、`结果*`、`template/模板` 类题目要求输出；
- `optimization_solver`：是否存在 solve/solver/optimize/pulp/ortools/cvxpy/scipy.optimize 等求解证据；
- `simulation`：是否存在 Monte Carlo/仿真/风险/情景/鲁棒证据；
- `model_comparison`：是否存在 baseline/compare/benchmark/对比证据；
- `sensitivity_analysis`：是否存在敏感性/扰动/鲁棒/消融证据；
- `paper_assets`：图表、表格、报告资产；
- `review_notes`：自动发现的阻塞或薄弱项。

## 严格模式

`--strict` 下，如果仍有：

- placeholder/TODO/链路测试表述；
- checker 未通过或没有明确 `issue_count=0`；

则返回非零退出。

## 使用原则

1. Evidence builder 只负责“证据索引”，不证明数学正确。
2. 如果它误判，优先在项目中补明确证据，而不是关闭门禁。
3. 项目特定 checker 跑完后，应把真实 `issue_count` 写入相关日志或 `competition_evidence.json`。
4. 冲奖目标下，`competition_evidence.json` 应成为提交前复盘清单：看得见什么已经完成、什么还只是口头说完成。
