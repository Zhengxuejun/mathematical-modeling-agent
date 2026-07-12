# 自动化执行器工作流

本文件定义 `mathematical-modeling-agent` 从“文档型技能”升级为“闭环执行型技能”时的默认自动化流程。

## 1. 项目创建

使用：

```bash
python ~/.hermes/skills/data-science/mathematical-modeling-agent/scripts/create_modeling_project.py "项目名" --base ~/Documents/数学建模
```

脚本必须创建：

- 标准目录 `00_题目与资料` 至 `07_提交包`；
- `README.md`；
- `requirements.txt`；
- `project_meta.json`；
- `06_过程记录/状态机/PROJECT_STATE.md`；
- `06_过程记录/一致性检查/report_consistency_check.md`；
- `06_过程记录/失败模式排雷/failure_pattern_log.md`；
- `06_过程记录/竞赛质控/` 下的交付物、PoC、模型交接、数学核验、运行/结果/主张/图表、评委风险和合规模板；
- `02_代码/00_data_audit.py` 至 `17_contest_qc.py`。

## 2. 状态推进

每完成一个阶段，必须更新 `PROJECT_STATE.md`：

| 状态 | 最低证据 |
|---|---|
| S0 材料获取 | 题面/附件路径 |
| S1 题目解析完成 | `problem_analysis.md` |
| S2 数据审计完成 | `data_audit.csv` |
| S3 基线模型完成 | baseline 结果表/日志 |
| S4 核心模型完成 | 主模型结果表/日志 |
| S5 敏感性/鲁棒性完成 | sensitivity 结果 |
| S6 报告初稿完成 | report draft |
| S7 一致性检查完成 | `report_consistency_check.md` |
| S8 最终提交包完成 | `README_submit.md` + `SHA256SUMS.txt` |

禁止只用口头说明替代证据路径。

## 3. 基线优先

任何有数据题默认执行：

```bash
python 02_代码/00_data_audit.py
python 02_代码/02_baseline.py
```

脚手架生成的 `00_data_audit.py`、`02_baseline.py`、`03_model_main.py`、`04_sensitivity.py` 必须保持 **Python 标准库即可运行** 的轻量闭环：先生成数据审计、数值列 baseline、baseline-derived 主结果占位和扰动敏感性表，确保 S2-S5 不因 `pandas/sklearn/xgboost` 等依赖缺失而卡死。重依赖模型只能作为题目定制增强项，不能成为默认闭环前提。

如果 baseline 暂时无法实现，必须在 `failure_pattern_log.md` 说明原因，而不能直接跳到复杂模型。

## 4. 最终质量门禁

提交前先运行：

```bash
python ~/.hermes/skills/data-science/mathematical-modeling-agent/scripts/modeling_pipeline.py . --zip
```

该命令会串联：

```text
data_audit
→ model_skeleton + domain_checker_templates
→ quality_gate + report_audit + state_update
→ finalize + state_update
→ quality_gate_plus + problem_coverage + result_interpretation + report_assembly
→ contest_qc(final) + repair_advisor
→ competition_evidence + competition_readiness
```

`contest_qc(final)` 会检查真实数据 PoC、模型交接、数学核验、可复现 run、结果/主张/图表映射、P0/P1 审查以及当前官方规则、匿名、复现和 AI 披露；它通过不等于模型一定正确或必然获奖。

如需分步调试，可手动运行：

```bash
python 02_代码/06_quality_gate.py
python ~/.hermes/skills/data-science/mathematical-modeling-agent/scripts/audit_report_consistency.py . --strict
python ~/.hermes/skills/data-science/mathematical-modeling-agent/scripts/problem_coverage_tracker.py .
python ~/.hermes/skills/data-science/mathematical-modeling-agent/scripts/result_interpretation_helper.py .
python ~/.hermes/skills/data-science/mathematical-modeling-agent/scripts/finalize_modeling_project.py . --entry 02_代码/03_model_main.py
```

如果需要严格模式：

```bash
python ~/.hermes/skills/data-science/mathematical-modeling-agent/scripts/modeling_pipeline.py . --strict --zip
```

或分步运行：

```bash
python ~/.hermes/skills/data-science/mathematical-modeling-agent/scripts/finalize_modeling_project.py . --strict --entry 02_代码/03_model_main.py
```

## 5. 输出解释

最终回复用户时至少给出：

- 当前状态 Sx；
- 已生成产物路径；
- 自动检查失败/警告数量；
- 是否可提交；
- 下一步只列必须动作，不列泛泛建议。

## 6. 不做的事

- 不删除原始数据；
- 不覆盖已有项目文件，除非用户明确允许或脚本使用 `--force`；
- 不把重构数据结果说成正式结论；
- 不把搜索资料替代官方题面；
- 不在未跑代码时编造数值。
