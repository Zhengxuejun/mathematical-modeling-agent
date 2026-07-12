# 数学建模智能体持续优化记录

本文件记录 `mathematical-modeling-agent` 从方法论技能升级为工程闭环技能时沉淀的可复用经验。它不是某次题目的流水账，而是后续优化该类技能时应继承的设计原则。

## 1. 优化方向优先级

当用户要求“继续优化数学建模智能体”时，优先顺序应是：

1. **减少低级错误**：题意、数据、单位、图表、摘要、结果表不一致。
2. **增强闭环执行**：脚手架、状态机、质量门禁、最终提交包。
3. **增强自动审计**：报告-图表-结果表-关键数值交叉核对。
4. **从真实题复跑中修误报**：优先修小问抽取、原始附件/结果表语境区分、轻依赖 baseline 等真实失败模式。
5. **最后再扩展模型库**：除非新题型明确暴露方法空缺，否则不要只堆模型名。

## 2. 已验证的工程化组件模式

### 项目脚手架

`create_modeling_project.py` 不应只创建目录，还应生成：

- 状态机 `PROJECT_STATE.md`；
- 报告一致性检查表；
- 失败模式排雷表；
- 数据审计、baseline、主模型、敏感性分析、图表生成、质量门禁脚本；
- `project_meta.json`。

### 质量门禁

提交前至少运行：

```bash
python 02_代码/06_quality_gate.py
python ~/.hermes/skills/data-science/mathematical-modeling-agent/scripts/audit_report_consistency.py . --strict
python ~/.hermes/skills/data-science/mathematical-modeling-agent/scripts/update_project_state.py .
python scripts/finalize_modeling_project.py . --strict --entry 02_代码/03_model_main.py
```

### 报告-结果自动审计

`audit_report_consistency.py` 应检查：

- 报告文件存在；
- 图表文件存在；
- 结果表存在；
- Markdown/LaTeX/DOCX 文本引用的图表/结果文件是否存在；
- 报告关键数字是否能在结果表中近似匹配；
- 常见单位是否被检测到；
- 输出 `auto_report_audit.md/json`。

## 3. 判定口径

- 明确缺失的报告、图表、结果表引用：`fail`。
- DOCX/PDF 无法深度自动解析：`warn`，提醒人工核对，不能假装通过。
- 数值匹配是辅助信号：普通模式 warning，严格数值模式可 fail。
- 自动审计只证明“一致性”，不能证明模型正确。

## 4. 工具与文件卫生

- Python 编译验证后产生的 `__pycache__` 不应留在技能目录。
- 清理缓存应移动到 macOS 回收站 `~/.Trash/`，不硬删除。
- 测试项目放 `~/test/`。
- 新增脚本必须真实运行 `py_compile` 和最小项目闭环测试。

## 5. 当前已实现：状态机自动推进器

已实现：

```text
scripts/update_project_state.py
references/state-updater.md
```

能力：根据项目现有文件自动判断 S0-S8 进度，并回写：

```text
06_过程记录/状态机/PROJECT_STATE.md
project_meta.json
```

检测逻辑：

| 状态 | 自动判断依据 |
|---|---|
| S0 | `00_题目与资料/` 或 `01_原始数据/` 有文件 |
| S1 | `06_过程记录/problem_analysis.md` 有实质内容 |
| S2 | `03_结果表格/data_audit.csv` 存在 |
| S3 | `*baseline*` 或 `*基线*` 结果存在 |
| S4 | `*model_results*` / `*main_model*` / `*core_model*` / `*主模型*` / `*核心模型*` 结果存在 |
| S5 | `*sensitivity*` / `*robust*` / `*敏感*` / `*鲁棒*` 结果存在 |
| S6 | `05_报告定稿/` 有报告 |
| S7 | `auto_report_audit.md` 与 `report_consistency_check.md` 存在 |
| S8 | `README_submit.md`、`SHA256SUMS.txt`、`submission_manifest.json` 存在 |

### 项目总控 Pipeline

已实现：

```text
scripts/modeling_pipeline.py
references/pipeline-runner.md
```

总控命令：

```bash
python scripts/modeling_pipeline.py <project> --strict --zip
```

它串联：

```text
data_audit → quality_gate → report_audit → state_update_pre_finalize → finalize → state_update_final → quality_gate_plus → problem_coverage → result_interpretation
```

并输出：

```text
06_过程记录/pipeline/pipeline_run_summary.md
06_过程记录/pipeline/pipeline_run_summary.json
```

`recommended_status=completed` 表示所有未跳过步骤 exit_code 均为 0；`highest_contiguous_state=S8` 表示状态机证据链闭环。

### Pipeline 严格模式暴露的报告引用问题

本轮验证中出现并确认了一个有价值的门禁信号：如果 `03_结果表格/` 中存在 `baseline_results.csv`、`sensitivity_results.csv` 等结果表，但报告正文只引用 `model_results.csv`，那么 `finalize_modeling_project.py --strict` 会因 `unreferenced_result_tables` 返回失败。

这不是误报，而是提交前应保留的风险提示：

- 若这些结果表是支撑材料，报告应显式引用或在附录/结果说明中说明；
- 若这些结果表只是中间调试产物，应移出最终结果目录或在打包策略中排除；
- 不能让未解释的旧表/中间表混入提交包，否则容易造成论文、附件和结果口径不一致。

因此 Pipeline 严格模式通过的推荐条件是：报告中的核心结论、baseline、主模型、敏感性/鲁棒性结果均有对应表格/图表引用，且结果目录不存在未解释的交付文件。

## 6. 已实现：增强质量门禁

已实现：

```text
scripts/quality_gate_plus.py
references/quality-gate-plus.md
```

能力：不仅检查文件存在，还检查 baseline/core/sensitivity 结果表是否可读非空、报告是否有逐问回答痕迹、图表/表格引用是否存在、project_meta 与状态机是否一致，并输出：

```text
06_过程记录/质量门禁/quality_gate_plus.md
06_过程记录/质量门禁/quality_gate_plus.json
```

## 7. 已实现：问题小问覆盖追踪器

已实现：

```text
scripts/problem_coverage_tracker.py
references/problem-coverage-tracker.md
```

目标：从 `problem_analysis.md` 抽取小问清单，检查报告、结果表和图表是否逐问覆盖，避免“模型和图很多，但漏答题目某一问”。

输出：

```text
06_过程记录/问题覆盖/problem_coverage.md
06_过程记录/问题覆盖/problem_coverage.json
```

已接入 `modeling_pipeline.py`，并在新项目脚手架中生成包装脚本：

```text
02_代码/09_problem_coverage.py
```

## 8. 已实现：模型结果解释生成器

已实现：

```text
scripts/result_interpretation_helper.py
references/result-interpretation-helper.md
```

目标：读取核心结果表、敏感性分析表、图表和覆盖追踪结果，生成每问的结论草稿、关键值摘要、图表解释方向和风险提示，减少报告写作时结果解释缺漏。

输出：

```text
06_过程记录/结果解释/result_interpretation_draft.md
06_过程记录/结果解释/result_interpretation_draft.json
```

已接入 `modeling_pipeline.py`，并在新项目脚手架中生成包装脚本：

```text
02_代码/10_result_interpretation.py
```

## 9. 已实现：证据优先报告拼装器

已实现：

```text
scripts/report_section_assembler.py
references/report-section-assembler.md
```

目标：读取 problem_analysis、result_interpretation_draft、problem_coverage、auto_report_audit 和质量门禁结果，拼装可编辑 Markdown 报告骨架，确保每问都有“直接结论—模型方法—证据表—图表解释—局限性”五段。

输出：

```text
05_报告定稿/report_draft.md
06_过程记录/报告拼装/report_section_assembly.md
06_过程记录/报告拼装/report_section_assembly.json
```

已接入 `modeling_pipeline.py`，并在新项目脚手架中生成包装脚本：

```text
02_代码/11_report_assembler.py
```

## 10. 已实现：修复建议器 / 交付摘要

已实现：

```text
scripts/repair_advisor.py
references/repair-advisor.md
```

目标：读取 quality_gate_plus、problem_coverage、result_interpretation、report_section_assembly、auto_report_audit、submission_manifest 和 pipeline 摘要，按优先级生成可执行修复清单，告诉用户“能不能交、还差什么、先修哪里”。

输出：

```text
06_过程记录/修复建议/repair_advice.md
06_过程记录/修复建议/repair_advice.json
```

已接入 `modeling_pipeline.py`，并在新项目脚手架中生成包装脚本：

```text
02_代码/12_repair_advisor.py
```

## 11. 当前已实现：竞赛就绪度门禁

已实现：

```text
scripts/competition_readiness_gate.py
references/competition-readiness-gate.md
```

目标：把“能跑完流程”与“能真正打比赛”分开。该门禁按三层判定：

```text
workflow_ready      # 工程闭环：材料、解析、结果表、报告、pipeline
model_ready         # 正式模型：非 placeholder，有题目特定模型、非空结果、领域 checker
competition_ready   # 可参赛评审口径：逐问覆盖、模型对比、敏感/鲁棒/风险分析、论文资产、一致性审计
```

输出：

```text
06_过程记录/竞赛就绪度/competition_readiness.md
06_过程记录/竞赛就绪度/competition_readiness.json
```

新项目脚手架会生成包装脚本：

```text
02_代码/13_competition_readiness.py
```

Pipeline 已接入 `competition_readiness` 步骤，并在摘要中展示 `competition_readiness` 与三层 fail/warn 数量。真实比赛/冲奖目标下，最终回复不能只报 `recommended_status=completed`，还必须报告竞赛就绪度口径；若停在 `model_not_ready` 或 `competition_needs_review`，优先修这些 warn/fail。

## 12. 当前已实现：竞赛证据自动汇总器

已实现：

```text
scripts/competition_evidence_builder.py
references/competition-evidence-builder.md
```

目标：在 `competition_readiness_gate.py` 前自动生成机器可读证据索引，减少门禁只靠关键词扫描。它输出：

```text
06_过程记录/competition_evidence.json
06_过程记录/competition_evidence.md
```

汇总内容包括：题目特定模型证据、placeholder 残留、领域 checker 与 issue_count、官方模板/题目要求输出、求解器、仿真/风险、模型对比、敏感性分析、论文资产和上游审计摘要。

新项目脚手架会生成包装脚本：

```text
02_代码/14_competition_evidence.py
```

Pipeline 已接入 `competition_evidence`，运行顺序为 `repair_advisor → competition_evidence → competition_readiness`。真实比赛项目中，若门禁误判，优先补充项目内显式证据和 checker issue_count，而不是关闭门禁。

## 13. 下一阶段优化方向

已完成一次真实题端到端复跑验证：`2024 MCM Problem C: Momentum in Tennis`。复跑项目：`~/Documents/数学建模/2024_MCM_C_Tennis_技能复跑_20260522`。

验证结果：最终 pipeline `recommended_status=completed`，`highest_contiguous_state=S8`，report_audit fail=0，quality_gate_plus fail=0，problem_coverage questions=5/missing=0，repair_advisor `delivery_readiness=needs_review`。

真实复跑暴露出的下一阶段优先优化点：

1. **增强小问抽取（已修）**：`problem_coverage_tracker.py` 已支持 `### Q1`、`## Q1`、`Q1:`、`Problem 1` 等格式，避免 questions=0。
2. **区分原始附件与结果表引用（已修）**：`audit_report_consistency.py` 与 `finalize_modeling_project.py` 已识别原始附件/数据字典文件名，记录 `raw_table_refs_ignored`，不再误判为缺失结果表；真正缺失的结果表仍 fail。
3. **结果解释软映射（已修）**：`result_interpretation_helper.py` 已按表名、列名、前几行文本、题目关键词和领域别名做软映射，支持无 Q 编号结果表与“一张表覆盖多问”的常见真实题场景。
4. **轻依赖优先（已修）**：脚手架默认 `00_data_audit.py`、`02_baseline.py`、`03_model_main.py`、`04_sensitivity.py` 已改成 Python 标准库即可运行；requirements 中把 scikit-learn/seaborn 降级为可选增强项，避免核心闭环因重依赖缺失中断。
5. **报告拼装 raw-data 标记（已修）**：`report_section_assembler.py` 已从 `problem_analysis.md` 和 `00_题目与资料/`、`01_原始数据/` 识别原始附件/数据文件，在报告骨架中单独标注“原始数据引用，非结果表证据”，并在 assembly JSON/MD 中记录 `raw_data_refs`，避免触发表格引用审计误杀。

真实题复跑暴露的 5 个高优先级问题已全部修完。下一步若继续优化，优先从真实课程/竞赛题中再跑一轮端到端闭环，寻找新的非臆想失败模式。

## 14. 会话沉淀：连续优化时的执行纪律

本轮会话暴露并固化了一个关键工作方式：当用户连续说“继续优化”时，不应停在规划或建议层，而应每轮选择一个最有杠杆的组件直接落地、验证、接入 SKILL.md，并更新持续优化记录。

推荐循环：

```text
读取当前技能索引
→ 选择 notes 中优先级最高的下一组件
→ 写 scripts/references/templates
→ 更新 SKILL.md 指针
→ 最小项目真实验证
→ 清理 __pycache__ 到 ~/.Trash
→ 更新 continuous-optimization-notes.md 的“已实现/下一阶段”
```

已验证的优化序列：

```text
失败模式库/一致性 checklist
→ 项目脚手架与最终打包
→ 报告-结果自动审计
→ 状态机自动推进器
→ 项目总控 pipeline
→ 智能质量门禁增强器 quality_gate_plus
→ 问题小问覆盖追踪器 problem_coverage_tracker
→ 模型结果解释生成器 result_interpretation_helper
→ 证据优先报告拼装器 report_section_assembler
→ 修复建议器 / 交付摘要 repair_advisor
→ 下一步：真实题端到端复跑验证
```

注意：这类技能维护任务的价值在“可运行组件 + 验证证据”，不是在回复里列更多想法。

## 15. 当前已实现：题型路由后的模型骨架生成器

已实现：

```text
scripts/model_skeleton_router.py
references/model-skeleton-router.md
```

目标：在“竞赛就绪度门禁/证据汇总器”之前补上建模生产层的第一步。它读取 `06_过程记录/problem_analysis.md`，自动识别优化、预测、评价、仿真、路径/网络、统计检验等题型，并生成：

```text
06_过程记录/model_skeleton/model_skeleton.json
06_过程记录/model_skeleton/model_skeleton.md
```

加 `--write-code` 时生成 starter：

```text
02_代码/generated_skeleton/model_main_skeleton.py
02_代码/generated_skeleton/check_constraints_skeleton.py
02_代码/generated_skeleton/sensitivity_skeleton.py
```

Pipeline 已接入 `model_skeleton`，默认位于 `data_audit → model_skeleton → quality_gate`。同时新增 `--skeleton-only`，用于 S1 早期只跑 data_audit/model_skeleton/quality_gate，避免在还没有结果表和报告时被终稿门禁误杀。新项目脚手架生成包装脚本：

```text
02_代码/15_model_skeleton.py
```

口径：`model_skeleton` 只是路线起点，不等于 `model_ready`。正式比赛中必须把骨架替换成题目特定可运行模型，运行领域 checker，并通过 `competition_evidence` 与 `competition_readiness`。


## 16. 当前已实现：领域 checker 模板库

已实现：

```text
scripts/domain_checker_template_builder.py
references/domain-checker-template-builder.md
```

目标：把 `model_skeleton_router.py` 的题型路由结果转成可执行 checker starter，覆盖优化、路径/网络、预测、评价、仿真、统计和 unknown 兜底。

输出：

```text
06_过程记录/领域checker/domain_checker_templates.json
06_过程记录/领域checker/domain_checker_templates.md
02_代码/generated_checkers/check_<type>.py
```

Pipeline 已接入 `domain_checker_templates`，位于 `model_skeleton → domain_checker_templates → quality_gate`。新项目脚手架生成包装脚本：

```text
02_代码/16_domain_checker_templates.py
```

口径：生成 checker 模板不等于正式 checker 证据。模板默认含 TODO/warn；必须把 TODO 替换为读取正式结果表、参数表、路线表、预测表或评价矩阵的硬检查，运行后 `issue_count=0`，才能作为 `competition_evidence.domain_checker` 的 model_ready 证据。


## 17. 当前已实现：竞赛证据与领域 checker 联动

已实现：

```text
scripts/competition_evidence_builder.py  # 增强
references/competition-evidence-checker-link.md
```

目标：防止证据汇总器把 `domain_checker_template_builder.py` 生成的 checker 模板误认为正式 checker 通过。

现在 `competition_evidence.json` 中的 `domain_checker.implementation.status` 区分：

```text
not_detected
checker_detected_no_machine_output
template_checker_only
implemented_checker_warn
implemented_checker_fail
implemented_checker_pass
```

只有 `implemented_checker_pass` 才能让 `domain_checker.status=pass`。要求正式 checker 输出存在、`issue_count=0`、`warn_count=0` 且无 TODO/template/starter 残留。

已用测试项目验证：仅存在 generated_checkers 时，证据汇总器输出 `domain_checker=template_checker_only`，不会误判为 model_ready。

## 18. 当前已实现：Contest QC 证据候选同步器

已实现：

```text
scripts/contest_evidence_sync.py
02_代码/18_contest_evidence_sync.py
```

目标：减少正式比赛中手工维护 `deliverable_matrix.csv`、`result_registry.csv` 和 `figure_evidence.csv` 的操作量。同步器从 `problem_analysis.md`、项目内结果表/图表以及 completed run 的精确输出路径发现候选，只补空字段并保留人工非空值。

安全边界：新行固定为 `candidate`；不会生成数学核验、论文主张、视觉通过或合规状态，也不会把文件存在解释为 `paper_ready`。写盘采用锁、表头验证、临时文件、备份、事务日志、回滚和启动恢复。Pipeline 顺序为：

```text
report_audit → state_update_pre_finalize → contest_evidence_sync → contest_qc
```

同步失败会跳过 Contest QC 并阻止最终打包，防止陈旧门禁结果被误用。下一阶段优先建设真实竞赛 benchmark harness，再引入带执行指标的候选方案树；不要先扩展更多模型名称。
