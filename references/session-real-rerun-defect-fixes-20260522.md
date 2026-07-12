# 会话沉淀：真实题复跑缺陷批量修复（2026-05-22）

本记录沉淀一次真实 MCM Tennis 复跑后，对 `mathematical-modeling-agent` 做的通用工程修复。它不是单题流水账，而是后续处理建模技能回归缺陷时的参考。

## 背景

在 2024 MCM Problem C: Momentum in Tennis 端到端复跑中，pipeline 已可跑到 S8，但暴露出若干真实题常见失败模式：

1. `problem_analysis.md` 中 `### Q1` / `## Q1` 等标题式小问抽取不稳。
2. 报告提到 `Wimbledon_featured_matches.csv`、`data_dictionary.csv` 等原始附件时，审计器容易误判为缺失的结果表。
3. 结果解释器过度依赖 `q1_*.csv` 这种命名，无法把 `model_results.csv`、`randomness_test_results.csv` 等泛结果表映射到小问。
4. 新项目脚手架 baseline/data audit 依赖偏重，缺 pandas/sklearn 时核心闭环可能中断。
5. 报告拼装器从问题解析继承数据清单时，没有显式标注 raw-data 语义。

## 已修复的通用能力

### 1. 小问抽取增强

`problem_coverage_tracker.py` 已支持更广的标题/列表格式，例如：

```text
### Q1 Momentum definition
## Q2 Randomness test
Q3: Predict swing points
Problem 4 Sensitivity analysis
```

后续新增抽取规则时，应用真实 `problem_analysis.md` 文本做回归，不要只测理想 bullet list。

### 2. 原始附件 vs 结果表引用区分

`audit_report_consistency.py` 与 `finalize_modeling_project.py` 增加 raw/reference table 识别。以下文件名/目录语境默认是原始数据或题面附件，不按 `03_结果表格/` 结果表缺失处理：

```text
01_原始数据/
00_题目与资料/
raw/input/source/original/dataset/data_dictionary/dictionary
featured_matches/Wimbledon_featured_matches/附件/原始/题目/数据字典
```

但如果文件名同时带有结果语义，例如 `model_results.csv`、`sensitivity_results.csv`，仍按结果表引用检查。

### 3. 结果解释软映射

`result_interpretation_helper.py` 不再只依赖 Q 编号命名，也读取：

```text
表名
列名
前 10 行文本
关键值摘要
图表文件名
题目关键词
coverage keywords
```

并加入常见建模题领域别名：

```text
momentum → serve / adjusted / point / ewma / alpha / 动量 / 发球 / 优势
randomness → permutation / p_value / run / streak / 随机 / 置换 / 检验
swing → prediction / auc / accuracy / 转折 / 预测
sensitivity → robust / alpha / parameter / scenario / 敏感 / 鲁棒
recommend → strategy / coach / suggestion / 建议 / 策略
evaluate → score / rank / indicator / 评价 / 得分 / 指标
forecast → predict / trend / future / 预测 / 趋势
optimize → objective / constraint / route / 优化 / 约束 / 路径
```

对 `model_results.csv`、`main_model_results.csv`、`results_summary.csv` 等泛结果表，如果内容与小问关键词相交，也允许匹配。

### 4. 轻依赖 baseline 优先

`create_modeling_project.py` 生成的默认脚本应保证没有 pandas/sklearn 也能跑通基础闭环：

```text
00_data_audit.py   标准库 csv/json/pathlib 审计 CSV/JSON，XLSX 标为 optional deep audit
02_baseline.py     生成 baseline_results.csv，统计数值列 count/mean/min/max
03_model_main.py   基于 baseline_results.csv 生成 model_results.csv，并明确 placeholder 语义
04_sensitivity.py  生成 sensitivity_results.csv，做 ±5%/±10% 等轻量扰动
```

`requirements.txt` 中 `scikit-learn`、`seaborn` 只作为可选增强项，不应成为核心 scaffold 的前提。

### 5. 报告拼装 raw-data 标记

`report_section_assembler.py` 现在会扫描：

```text
00_题目与资料/
01_原始数据/
06_过程记录/problem_analysis.md
```

并输出：

```text
raw_data_files
raw_data_refs
```

生成的 `report_draft.md` 中新增“原始数据引用（非结果表证据）”小节，例如：

```text
- `01_原始数据/Wimbledon_featured_matches.csv`：原始数据引用，非 `03_结果表格/` 的结果证据表。
- `00_题目与资料/data_dictionary.csv`：原始数据引用，非 `03_结果表格/` 的结果证据表。
```

目的：让问题重述/数据处理部分可以安全说明原始附件，而不会触发结果表引用审计误杀。真正支撑结论的表格仍必须放在 `03_结果表格/` 并在逐问“证据表”中引用。

## 回归验证口径

修复这类缺陷时，至少做三层验证：

1. `python3 -m py_compile` 编译新增/修改脚本。
2. 在 `~/test/` 构造最小项目，验证目标缺陷被修复。
3. 如果涉及报告引用，必须跑 `audit_report_consistency.py` 或 pipeline，确认不会产生新的误杀。

文件卫生：`__pycache__` 不留在技能目录；清理时移动到 `~/.Trash/`，不硬删除。

## 当前状态

真实复跑暴露的 5 个高优先级缺陷已全部修完。后续不要继续凭空堆检查器，优先拿新的真实课程/竞赛题再跑端到端闭环，用新的真实失败模式驱动下一轮技能更新。
