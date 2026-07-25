# 数学建模项目 README 模板

> 项目名称：【比赛/课程/题目名称】  
> 题号：【A/B/C/...】  
> 创建时间：【YYYY-MM-DD】

## 1. 项目概况

- 任务类型：【优化 / 预测 / 评价 / 仿真 / 综合】
- 数据来源：【题目附件 / 公开数据 / 手工整理】
- 最终产物：【报告 / 代码 / 图表 / 提交包】

## 2. 目录结构

```text
00_题目与资料/       # 题面、附件说明、参考资料
01_原始数据/         # 原始数据，只读不手改
02_代码/             # Python/R/Matlab 等代码
03_结果表格/         # CSV/XLSX/JSON 结果
04_图表/             # PNG/PDF/SVG 图表
05_报告定稿/         # DOCX/PDF/LaTeX/Markdown
06_过程记录/         # 草稿、实验日志、截图
07_提交包/           # 最终提交文件
08_候选方案/         # 候选模型、运行记录和改进分支
```

## 3. 子任务 DAG

| 任务 | 说明 | 输入 | 输出 | 状态 |
|---|---|---|---|---|
| T0 | 题目解析与数据审计 | 题面、附件 | problem_analysis.md | 待完成 |
| T1 | 数据清洗与特征构造 | 原始数据 | processed data | 待完成 |
| T2 | 基线模型 | processed data | baseline results | 待完成 |
| T3 | 核心模型 | processed data | model results | 待完成 |
| T4 | 敏感性/鲁棒性分析 | model results | sensitivity results | 待完成 |
| T5 | 报告整合 | all results | final report | 待完成 |

## 4. 运行环境

```bash
python --version
pip install -r requirements.txt
```

推荐基础依赖：

```text
pandas
numpy
scipy
scikit-learn
matplotlib
seaborn
openpyxl
```

优化类题目可按需添加：

```text
pulp
ortools
cvxpy
networkx
```

## 5. 复现步骤

```bash
python 02_代码/00_data_audit.py
python 02_代码/01_preprocess.py
python 02_代码/02_baseline.py
python 02_代码/03_model_main.py
python 02_代码/04_sensitivity.py
python 02_代码/05_make_figures.py
python 02_代码/19_candidate_solution_tree.py init --objective-metric objective --direction maximize
# 正式 run 审核完成后，将 R1 替换为真实 run_id
python 02_代码/17_contest_qc.py --freeze-run R1 --phase final --strict
```

正式 run 必须填写非空 `command` 和明确 `input_files`；确实没有外部输入时填写 `not_applicable`。冻结命令不会执行运行记录中的命令；它只记录正式 run 所声明入口、输入、结果表和图表的 SHA256。冻结后的文件如有变化，必须重跑、重审并再次显式冻结，不能直接沿用旧 `paper_ready` 状态。

## 6. 关键结果

| 问题 | 方法 | 关键结果 | 对应文件 |
|---|---|---|---|
| 问题一 | 【模型】 | 【结论】 | 03_结果表格/... |
| 问题二 | 【模型】 | 【结论】 | 03_结果表格/... |
| 问题三 | 【模型】 | 【结论】 | 03_结果表格/... |

## 7. 图表清单

| 图号 | 文件 | 说明 | 正文位置 |
|---|---|---|---|
| 图1 | 04_图表/...png | 【说明】 | 第 x 节 |
| 图2 | 04_图表/...png | 【说明】 | 第 x 节 |

## 8. 最终提交

最终提交文件位于：`07_提交包/`

- `report.pdf`
- `report.docx`（若需要）
- `source_code.zip`（若需要）
- `README_submit.md`

## 9. 备注

- 原始数据不得手工覆盖。
- 所有中间结果必须可由代码重新生成。
- 桌面不得保留散落临时文件。
