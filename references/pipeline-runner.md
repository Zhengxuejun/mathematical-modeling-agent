# 项目总控 Pipeline

`modeling_pipeline.py` 是 `mathematical-modeling-agent` 的一条命令总控运行器，用于把分散的审计、状态推进和提交包生成串成可复现闭环。

## 1. 目标

解决的问题：

- 提交前命令太分散，容易漏跑质量门禁或状态更新；
- `audit_report_consistency.py`、`update_project_state.py`、`finalize_modeling_project.py` 各自有输出，但缺少统一摘要；
- 项目是否可提交需要一个机器可读和人类可读的总控结果。

Pipeline 证明的是：**工作流证据是否闭环**。它不能证明模型一定正确，模型合理性仍需读题、数据审计、公式检查和人工/智能体复核。

## 2. 脚本路径

```text
scripts/modeling_pipeline.py
```

新建项目后也会生成包装脚本：

```text
02_代码/08_pipeline.py
```

## 3. 标准用法

在项目根目录执行：

```bash
python 02_代码/08_pipeline.py --zip
```

或使用技能脚本绝对路径：

```bash
python ~/.hermes/skills/data-science/mathematical-modeling-agent/scripts/modeling_pipeline.py . --zip
```

严格模式：

```bash
python 02_代码/08_pipeline.py --strict --zip
```

严格数值匹配：

```bash
python 02_代码/08_pipeline.py --strict --strict-numbers --zip
```

指定入口脚本：

```bash
python 02_代码/08_pipeline.py --entry 02_代码/03_model_main.py --zip
```

指定报告：

```bash
python 02_代码/08_pipeline.py --report 05_报告定稿/report.md --zip
```

## 4. 执行步骤

默认执行：

```text
1. data_audit
   运行 02_代码/00_data_audit.py

2. model_skeleton / domain_checker_templates
   根据题目解析路由模型骨架，并生成不可冒充正式证据的 checker 起点

3. quality_gate / report_audit / state_update_pre_finalize
   运行基础质量门禁、报告-结果审计并记录打包前状态

4. finalize / state_update_final
   生成提交包并重新识别 S8

5. quality_gate_plus / problem_coverage / result_interpretation / report_assembly
   审查结果表、逐问覆盖、解释草稿和报告证据骨架

6. contest_qc
   运行 `contest_qc_gate.py --phase final`，检查交付物锁定、真实数据 PoC、模型交接、数学核验、可复现 run、主张/图表证据、P0/P1 风险和提交合规

7. repair_advisor / competition_evidence / competition_readiness
   汇总最小修复路径、自动证据索引和 workflow/model/competition 三层就绪度
```

可跳过项：

```bash
--skip-data-audit
--skip-quality-gate
--skip-report-audit
--skip-quality-plus
--skip-coverage
--skip-interpretation
--skip-report-assembly
--skip-contest-qc
--skip-repair-advisor
--skip-competition-evidence
--skip-competition-readiness
--skip-finalize
```

跳过只应用于调试或局部检查，正式提交前不建议跳过。

## 5. 输出文件

Pipeline 会生成：

```text
06_过程记录/pipeline/pipeline_run_summary.json
06_过程记录/pipeline/pipeline_run_summary.md
```

摘要包含：

- 每一步命令；
- exit_code；
- 用时；
- stdout/stderr 尾部；
- 报告一致性审计 pass/warn/fail；
- 增强质量门禁 pass/warn/fail；
- 问题覆盖追踪 questions/missing/weak_assets；
- 结果解释草稿 questions/without_tables/warn/fail；
- 竞赛质控 `contest_qc_readiness` 与 pass/warn/fail；
- 竞赛就绪度 workflow/model/competition 分层统计；
- 最终打包检查 warn/fail；
- `recommended_status`；
- `highest_contiguous_state`；
- 提交包目录。

## 6. 推荐状态口径

`recommended_status` 同时反映**所选步骤的执行结果**和**S0-S8 项目进度**，避免将局部检查误写成项目完成：

```text
completed          所有未跳过步骤成功，且 highest_contiguous_state = S8
early_stage_passed --skeleton-only 的早期路由/审计步骤成功，但项目尚未完整交付
in_progress        所有未跳过步骤成功，但 S0-S8 证据尚未到 S8
failed             至少一个未跳过步骤失败
```

失败时先看：

```text
06_过程记录/pipeline/pipeline_run_summary.md
```

再进入对应脚本输出：

```text
06_过程记录/一致性检查/auto_report_audit.md
07_提交包/submission_manifest.json
06_过程记录/状态机/PROJECT_STATE.md
```

## 7. 与 S0-S8 状态机关系

Pipeline 会在 finalize 前后各运行一次 `update_project_state.py`：

- 第一次：记录打包前状态；
- 第二次：打包后重新识别 S8。

因此完整闭环项目应看到：

```text
highest_contiguous_state = S8
recommended_status = completed
```

如果状态未到 S8，`recommended_status` 必须为 `early_stage_passed` 或 `in_progress`，而不是 `completed`。常见原因：

- 前序证据缺失，例如 baseline/sensitivity 结果文件命名不符合状态机规则；
- 用户主动 `--skip-finalize`；
- 项目还不是完整提交态，只是局部检查通过。

## 8. 注意事项

- Pipeline 不删除原始数据。
- 默认不复制原始数据，除非使用 `--include-raw-data`。
- 默认复制代码，除非使用 `--no-code`。
- `--strict` 会把 audit/finalize 支持的 warning 提升为失败。
- `--strict-numbers` 适合终稿前使用；早期草稿可能因数字尚未同步而失败。
- PDF 仍不做深度解析；DOCX 只抽文本，不做视觉级排版检查。
