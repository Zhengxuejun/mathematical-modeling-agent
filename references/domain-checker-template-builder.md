# 领域 checker 模板库

## 目标

`domain_checker_template_builder.py` 把 `model_skeleton_router.py` 的题型识别结果转成可执行 checker 模板，解决“知道该建什么模型，但不知道怎样证明没建错”的问题。

它覆盖常见竞赛题型：

- 优化/资源配置；
- 路径/网络/物流；
- 预测/回归；
- 综合评价；
- 仿真/随机情景；
- 统计检验；
- unknown 通用兜底。

## 输入

优先读取：

```text
06_过程记录/model_skeleton/model_skeleton.json
```

如果没有模型骨架，会退回生成通用 checker；严格模式下会失败。

## 输出

索引文件：

```text
06_过程记录/领域checker/domain_checker_templates.json
06_过程记录/领域checker/domain_checker_templates.md
```

生成的 checker 脚本：

```text
02_代码/generated_checkers/check_optimization.py
02_代码/generated_checkers/check_network_routing.py
02_代码/generated_checkers/check_simulation.py
...
```

默认最多为排名前三的题型生成 checker，可用 `--max-types` 调整。

## 命令

```bash
python ~/.hermes/skills/data-science/mathematical-modeling-agent/scripts/domain_checker_template_builder.py <project>
```

严格要求已有模型骨架：

```bash
python ~/.hermes/skills/data-science/mathematical-modeling-agent/scripts/domain_checker_template_builder.py <project> --strict
```

覆盖旧模板：

```bash
python ~/.hermes/skills/data-science/mathematical-modeling-agent/scripts/domain_checker_template_builder.py <project> --force
```

## 重要口径

生成的 checker 是模板，不是正式约束检查证据。模板默认会输出 TODO/warn，只有把 TODO 替换为读取正式结果表、参数表、路线表、预测表、评价矩阵等的硬检查后，才能作为 `competition_evidence.domain_checker` 的正式依据。

不要因为 checker 文件存在就宣称 `model_ready`。必须满足：

```text
正式 checker 已实现
→ 运行完成
→ issue_count=0
→ 结果表/参数表可复算
→ competition_evidence 收集到该证据
```

## 典型检查项

### 优化类

- 容量/预算/面积不超限；
- 覆盖/唯一性/分配逻辑；
- 变量上下界/整数/0-1；
- 目标函数复算；
- 求解状态与 gap。

### 路径/网络/物流类

- 节点访问次数；
- 路径连续性；
- 车辆容量；
- 时间窗；
- 距离/成本复算；
- 路径可视化。

### 预测类

- 训练/验证/测试切分；
- 数据泄漏；
- baseline；
- 误差指标；
- 残差诊断。

### 综合评价类

- 指标方向；
- 标准化范围；
- 权重和；
- 得分/排序复算；
- 排序稳定性。

### 仿真类

- 固定随机种子；
- 分布参数来源；
- 情景数量与收敛；
- 风险指标；
- 极端情景可行性。

### 统计类

- 独立性/重复测量；
- 检验前提；
- 多重检验；
- 效应量与置信区间；
- 稳健模型。
