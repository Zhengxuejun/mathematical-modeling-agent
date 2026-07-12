# AIDE 式候选方案树

## 定位

`candidate_solution_tree.py` 管理同一建模问题的有限候选实验。它记录 baseline、父子改进假设、运行证据、输入快照、验证分数、目标值和可选 Benchmark 结果，避免比赛中只保留“最后一次代码”而丢失模型探索依据。

这是候选搜索模式的独立实现，不包含 AIDE 项目的源码、提示词、数据集或执行器。

## 初始化

```bash
python 02_代码/19_candidate_solution_tree.py init \
  --objective-metric objective \
  --direction maximize \
  --validation-metric validation_score \
  --max-candidates 12 \
  --max-depth 3
```

目标值方向只决定同等门禁与验证水平下的排序。`validation_score` 必须归一化到 `[0, 1]`；分类、预测、优化、评价题应根据真实验证方案计算它，不能用训练集拟合分数冒充。

## 候选契约

每个 `08_候选方案/<name>/` 至少包含：

```text
solution.json
run_record.json
report.md
artifacts/
```

`solution.json` 记录模型身份、seed、`metrics`、`checks.feasible`、`checks.validation_passed` 和证据路径。`run_record.json` 记录命令、运行时间、退出码、项目内输入哈希和候选内产物哈希。

候选树只读取这些产物，不执行记录的命令。输入或证据缺失、路径逃逸、哈希不符、非有限指标、非零退出码、不可行或验证失败都会保留为 `blocked` 节点。
每次选优前还会复核评估快照；若控制文件、输入或证据在评估后发生变化，节点必须重新评估，不能沿用陈旧分数。

## 登记与评估

```bash
python 02_代码/19_candidate_solution_tree.py add \
  --submission 08_候选方案/baseline \
  --label baseline \
  --hypothesis "建立可复现基线"

python 02_代码/19_candidate_solution_tree.py add \
  --submission 08_候选方案/robust \
  --parent C001 \
  --label robust \
  --hypothesis "分组验证降低泄漏风险"

python 02_代码/19_candidate_solution_tree.py evaluate --candidate C001
python 02_代码/19_candidate_solution_tree.py evaluate --candidate C002
```

若候选与某个公开 Benchmark case 契约兼容，可以增加：

```bash
python 02_代码/19_candidate_solution_tree.py evaluate \
  --candidate C002 \
  --benchmark-case /path/to/benchmarks/cases/<case_id>
```

只要一个合格节点带有 Benchmark，所有参与选优的合格节点就必须使用同一 case hash；所有节点也必须具有完全一致的输入路径/哈希集合。

## 选优

```bash
python 02_代码/19_candidate_solution_tree.py select
python 02_代码/19_candidate_solution_tree.py status
```

排序依次比较：同 case Benchmark、验证分数、目标方向、证据数量、运行时间和候选 ID。报告位于：

```text
06_过程记录/候选方案树/candidate_tree.json
06_过程记录/候选方案树/candidate_tree.md
```

`selected` 只表示当前树配置下最强的合格实验，不等于正式模型已证明正确，也不会更新 `paper_ready`、`final_ready`、`competition_ready`、S0-S8 或提交包。选中后仍需运行题目特定 checker、敏感性/鲁棒性分析、Contest QC 和竞赛就绪度门禁。
