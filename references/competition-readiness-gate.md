# 竞赛就绪度门禁 / Competition Readiness Gate

`competition_readiness_gate.py` 用于把数学建模项目从“工程闭环”进一步区分到“可参赛/冲奖口径”。

它解决的核心问题：`S0-S8 completed` 只能证明项目文件链路跑通，不能证明题目已经真正建模、可提交、更不能证明具备获奖竞争力。

## 命令

```bash
python ~/.hermes/skills/data-science/mathematical-modeling-agent/scripts/competition_readiness_gate.py <project>
python ~/.hermes/skills/data-science/mathematical-modeling-agent/scripts/competition_readiness_gate.py <project> --strict
```

新建项目脚手架内也会生成包装脚本：

```bash
python 02_代码/13_competition_readiness.py
```

终稿前先运行质控账本门禁：

```bash
python 02_代码/17_contest_qc.py --freeze-run R1 --phase final --strict
```

将 `R1` 替换为支撑论文证据的正式 run_id；多个 run 逐个冻结后再运行 final 门禁。`contest_qc_gate.json` 是交付物、真实数据 PoC、模型交接、数学核验、run/artifact/result/claim/figure 证据、P0/P1 风险与合规的真相源；`competition_evidence.json` 仍是自动发现/提示层，不能覆盖明确的 QC 阻塞。

## 输出

```text
06_过程记录/竞赛就绪度/competition_readiness.md
06_过程记录/竞赛就绪度/competition_readiness.json
```

## 分层口径

### 1. workflow_ready

证明项目工程链路完整：

- 题面/附件/原始数据存在；
- `problem_analysis.md` 存在且非空；
- 结果表存在；
- 报告/报告草稿存在；
- pipeline 如存在，状态正常。

### 2. model_ready

证明不再只是 placeholder：

- 未检测到 `placeholder`、`baseline-derived`、`TODO`、`待补充`、`仅用于链路测试` 等表述；
- 存在题目特定建模证据：变量、目标函数、约束、参数估计、算法/求解脚本；
- 结果表非空；
- 存在领域约束/可行性 checker 证据。

### 3. competition_ready

证明达到可参赛评审口径：

- 小问逐问覆盖；
- `contest_qc_gate.py --phase final` 为 `final_ready`，不存在未冻结/漂移产物、开放 P0/P1、主张/图表证据断链或提交合规缺口；
- baseline 或模型对比；
- 敏感性/鲁棒性/误差检验；
- 不确定性、风险或情景分析；
- 足够论文资产：关键结果表、对比图、敏感性图、流程/结构图等；
- 报告-结果一致性审计无 fail；
- repair advisor 不再阻塞。

`competition_ready` 不是保证获奖，而是表示当前项目满足“可以认真提交给评委”的最低可信标准。

## 推荐 evidence 文件

项目可以写入：

```text
06_过程记录/competition_evidence.json
```

用于显式告诉门禁哪些题目特定证据已经完成。示例：

```json
{
  "problem_specific_model": true,
  "domain_checker": {
    "path": "02_代码/check_constraints.py",
    "issue_count": 0
  },
  "official_templates_filled": [
    "03_结果表格/result1.xlsx",
    "03_结果表格/result2.xlsx"
  ],
  "optimization_solver": {
    "type": "MILP",
    "status": "optimal",
    "objective": 123456.7
  },
  "simulation": {
    "scenarios": 1000,
    "metrics": ["mean", "std", "q05", "cvar_5"]
  },
  "model_comparison": true,
  "sensitivity_analysis": true,
  "paper_assets": {
    "figures": 6,
    "tables": 5
  }
}
```

## 比赛执行建议

比赛中不要一开始就追求 `competition_ready`。正确顺序是：

```text
0–8h：workflow_ready + baseline
8–24h：model_ready，完成题目特定模型和 checker
24–48h：competition_needs_review，补验证、对比、风险分析、图表
48–72h：competition_ready，反复交叉审计和论文打磨
```

## 常见判定

- `workflow_blocked`：材料/解析/结果/报告链路不完整。
- `model_not_ready`：有项目文件，但仍是 placeholder 或缺领域模型/checker。
- `competition_needs_review`：模型能跑，但验证、对比、风险、论文资产不足。
- `competition_ready`：工程、模型、验证、论文均达到最低参赛可信标准。
