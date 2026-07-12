---
name: mathematical-modeling-agent
description: "数学建模智能体工作流：把开放式建模题转化为可验证的模型、代码、图表与论文/报告。吸收 MM-Agent/LLM-MM-Agent 的四阶段流程、HMML 方法检索思想与子任务 DAG 思维。"
version: 1.2.0
author: HM-AI
license: MIT
metadata:
  hermes:
    tags: [mathematical-modeling, mcm, icm, optimization, data-analysis, report-writing, python, modeling-agent]
    homepage: https://github.com/usail-hkust/LLM-MM-Agent
    related_skills: [vrp-solver, pdf-ppt-docx-xlsx, Word / DOCX]
---

# Mathematical Modeling Agent / 数学建模智能体

本项目是独立实现，工作流层面参考公开研究项目 `usail-hkust/LLM-MM-Agent`，不包含其源码、数据集、提示词、模型权重或媒体资源。仓库内 MIT 许可证仅适用于本仓库内容；复制上游材料时必须单独核对其当前许可条款。详见 `NOTICE`。

## 配套引用文件

加载本技能后，按任务需要读取以下文件：

- `references/model-library.md`：详细数学建模方法库与快速匹配表。
- `references/problem-type-routing.md`：题型路由与模型门禁，防止把复杂小问误套单一模型。
- `references/biostatistics-and-screening.md`：NIPT、医学筛查、重复测量、阈值达标时间与异常判定规则。
- `references/case-study-index.md`：案例库索引，根据题型和失败模式快速定位应加载案例。
- `references/modeling-failure-patterns.md`：建模失败模式库，用于读题、数据、统计、优化、报告和 AI 辅助建模排雷。
- `references/case-study-cumcm-2025-c-nipt.md`：2025 国赛 C 题 NIPT 案例。
- `references/session-model-skeleton-router-20260523.md`：本轮继续优化沉淀，记录题型路由后的模型骨架生成器 `model_skeleton_router.py`、`--skeleton-only` 早期 pipeline 模式、验证结果与下一步 domain checker 模板库方向。
- `references/case-study-cumcm-2024-c-crop-strategy-20260523.md`：2024 国赛 C 题农作物种植策略冲奖级升级案例，记录从 S0-S8 轻量闭环到 Excel 解析、官方模板填充、领域约束 checker、可行启发式/MIP 升级路线的 durable lessons。
- `references/project-state-machine.md`：S0-S8 建模项目状态机，定义每阶段产物、完成判据和回退规则。
- `references/topic-selection-rubric.md`：国赛/美赛前 1 小时选题评分器。
- `references/report-template.md`：国赛/美赛/课程报告写作模板。
- `references/competition-playbook.md`：真实比赛执行节奏、项目编排、交付与归档规范。
- `references/competition-readiness-gate.md`：竞赛就绪度门禁，区分 workflow_ready、model_ready、competition_ready，防止 S0-S8 闭环被误认为可参赛/可获奖。
- `references/contest-quality-gate.md`：竞赛质控账本与三阶段门禁说明。新建竞赛项目、主模型正式化或终稿提交前按需读取。
- `references/contest-qc-integration-audit-20260711.md`：质控账本接线与硬化审计；升级 scaffold、Pipeline 或 readiness 时读取。优先复用单一 `contest_qc_gate.py`，不要拆装成 17 个常驻子技能。
- `references/competition-evidence-builder.md`：竞赛证据自动汇总器，生成 `competition_evidence.json/md`，把模型、checker、求解器、仿真、敏感性和论文资产转成机器可读证据。
- `references/competition-evidence-checker-link.md`：竞赛证据与领域 checker 联动，区分 checker 模板、带 warning 的实现、失败实现和正式 pass 证据。
- `references/model-skeleton-router.md`：题型路由后的模型骨架生成器，根据 problem_analysis 自动识别优化/预测/评价/仿真/路径/统计题型，并生成变量、约束/checker、验证资产和 starter code。
- `references/domain-checker-template-builder.md`：领域 checker 模板库，把题型路由结果转成优化、路径、预测、评价、仿真、统计等可执行 checker starter。
- `references/session-competition-agent-generalization-and-checker-templates-20260523.md`：本轮通用数学建模智能体冲奖级优化沉淀，记录从“流程闭环”升级到“题型路由→模型骨架→领域 checker 模板→evidence/readiness”的质量控制链。
- `references/session-competition-grade-agent-upgrades-20260523.md`：本轮“真正打比赛/能获奖/继续优化”会话沉淀，记录通用数学建模智能体从赛后质检升级到赛中生产链：model_skeleton 路由、domain checker 模板、competition_evidence 对 checker 模板/正式 pass 的区分，以及 `--skeleton-only` 早期模式。
- `references/session-generalizing-competition-agent-20260523.md`：本轮用户纠偏沉淀，明确“能真正打比赛/能获奖”的优化目标应优先提升通用建模智能体能力，而不是继续专项优化某一道历史题；历史题应作为测试 fixture 暴露可复用缺陷。
- `references/session-generalizing-competition-agent-20260523.md`：本轮用户纠偏沉淀，明确“能真正打比赛/能获奖”的优化目标应优先提升通用建模智能体能力，而不是继续专项优化某一道历史题；历史题应作为测试 fixture 暴露可复用缺陷。
- `references/session-cumcm-2024-c-official-rerun-20260523.md`：本轮用 CUMCM 2024 C《农作物的种植策略》官方题与附件做真实题轻量 S0-S8 闭环测试，记录 Excel 多 sheet baseline 缺陷、报告审计误判路径与“闭环完成≠正式最优解”的表达边界。
- `references/case-study-huazhong-green-logistics-vrp-20260522.md`：华中杯绿色物流 VRP 复跑案例，记录缺失时间窗、数据审计、复跑结果与注意事项。
- `references/case-study-mcm-2024-c-tennis-20260522.md`：2024 MCM C 网球 momentum 真实题端到端复跑案例，记录 S8 pipeline 验证、轻依赖模型、审计误杀和小问抽取缺陷。
- `templates/project-README.md`：项目 README 模板。
- `templates/data-audit-excel.md`：多 sheet Excel 数据审计脚本模板，支持中文列名、比例字段、GC 质量控制和孕周解析。
- `scripts/create_modeling_project.py`：创建标准数学建模项目目录、状态机、一致性检查表、失败模式记录和质量门禁脚本。
- `scripts/audit_report_consistency.py`：自动审计报告与结果/图表/数值/单位一致性，输出 auto_report_audit.md/json。
- `scripts/update_project_state.py`：根据真实产物自动判断 S0-S8 状态；S8 必须通过 manifest v2.0、失败检查、文件清单和 SHA256 验证。
- `scripts/modeling_pipeline.py`：先完成报告拼装、审计、最终质控和竞赛就绪度检查，再执行原子打包与 S8 更新。仅有效 S8 为 `completed`；`--skeleton-only` 为 `early_stage_passed`，其他未失败项目为 `in_progress`。
- `scripts/quality_gate_plus.py`：增强质量门禁，检查结果表可读非空、baseline/core/sensitivity、报告逐问痕迹、图表/表格引用、状态与 meta 一致性。
- `scripts/problem_coverage_tracker.py`：问题小问覆盖追踪器，从 problem_analysis.md 抽取小问并检查报告、结果表、图表是否逐问覆盖。
- `scripts/result_interpretation_helper.py`：模型结果解释生成器，读取逐问覆盖、结果表和图表，生成每问结论草稿、关键值摘要与风险提示。
- `scripts/report_section_assembler.py`：证据优先报告拼装器，生成可编辑 `report_draft.md`；默认保留已存在的人工编辑报告，只有 `--force-report` 才覆盖。
- `scripts/repair_advisor.py`：修复建议器，汇总 pipeline、质量门禁、覆盖追踪、解释草稿、报告拼装和提交包检查，输出“能不能交、还差什么、先修哪里”。
- `scripts/finalize_modeling_project.py`：在干净 staging 目录生成 README、manifest v2.0 和 SHA256，自校验通过后原子替换正式提交包。
- `scripts/submission_package_contract.py`：finalizer 与 S8 状态机共享的提交包契约，验证路径边界、文件库存、失败检查和 SHA256。
- `scripts/competition_readiness_gate.py`：竞赛就绪度门禁，读取项目产物、审计 JSON、`contest_qc_gate.json` 与可选 `competition_evidence.json`，输出 workflow/model/competition 三层 readiness。
- `scripts/contest_qc_gate.py`：竞赛质控账本门禁；`--init` 非破坏性创建登记表，`--phase early|model|final` 检查交付物、真实数据 PoC、运行/结果/主张追溯、评委风险和提交合规。它是证据账本真相源，`competition_evidence_builder.py` 仅作启发式证据索引。
- `scripts/contest_evidence_sync.py`：Contest QC 待审核候选同步器；从小问、项目内结果表/图表和 completed run 精确路径关联生成 `candidate`，保留人工非空字段，并用可恢复事务防止半写入。文件发现不等于验证通过。
- `scripts/competition_evidence_builder.py`：竞赛证据自动汇总器，在门禁前生成 `06_过程记录/competition_evidence.json/md`，让模型/checker/仿真/敏感性/论文资产证据可审计；现已区分 `template_checker_only` 与 `implemented_checker_pass`。
- `scripts/model_skeleton_router.py`：模型骨架路由器，从 S1 题目解析生成题型、变量/参数、模型核心、领域 checker、验证资产与可选 starter code。
- `scripts/domain_checker_template_builder.py`：领域 checker 模板生成器，基于模型骨架路由生成 `02_代码/generated_checkers/check_*.py` 和模板索引。
- `references/automation-workflow.md`：自动化执行器工作流，规定建项目、状态推进、baseline-first、质量门禁和最终回复格式。
- `references/report-result-crosscheck.md`：报告-结果自动一致性检查口径，说明 Markdown/LaTeX 图表/结果引用如何与真实文件交叉核对。
- `references/report-result-audit-design.md`：报告-结果自动一致性检查增强设计；当用户要求继续优化提交前审计、自动核对图表/数值/附件时读取。
- `references/state-updater.md`：项目状态自动推进器说明，规定 S0-S8 的证据判据和连续完成状态口径。
- `references/pipeline-runner.md`：项目总控 Pipeline 说明，规定一条命令闭环、输出摘要和 recommended_status 口径。
- `references/quality-gate-plus.md`：增强质量门禁说明，规定结果表可读性、非空、报告逐问、状态一致性等检查口径。
- `references/problem-coverage-tracker.md`：问题小问覆盖追踪器说明，规定如何从 problem_analysis.md 抽取小问并做逐问覆盖审计。
- `references/result-interpretation-helper.md`：模型结果解释生成器说明，规定如何从结果表/图表生成逐问解释草稿与风险提示。
- `references/report-section-assembler.md`：证据优先报告拼装器说明，规定如何把逐问解释草稿、表格、图表和风险提示拼成可编辑 Markdown 报告骨架。
- `references/repair-advisor.md`：修复建议器说明，规定如何把各类审计结果汇总成优先级修复清单和交付 readiness 判断。
- `references/continuous-optimization-notes.md`：数学建模智能体持续优化记录，沉淀闭环执行、自动审计、文件卫生和下一阶段状态机自动推进器设计。
- `references/session-continuous-optimization-20260522.md`：本轮连续优化会话沉淀，记录从脚手架到 Pipeline/quality_gate_plus 的工程闭环升级模式、验证纪律和下一步 problem_coverage_tracker 方向。
- `references/session-problem-coverage-tracker-20260522.md`：问题小问覆盖追踪器实现沉淀，记录逐问抽取、覆盖判定、Pipeline 集成、正负例验证和下一步 result_interpretation_helper 方向。
- `references/session-result-interpretation-helper-20260522.md`：结果解释生成器实现沉淀，记录 problem_coverage 与 result_interpretation 的 Pipeline 集成、验证纪律和下一步 report_section_assembler 方向。
- `references/session-real-rerun-defect-fixes-20260522.md`：2024 MCM C Tennis 真实题复跑后暴露并修复的通用缺陷，包含 Q 标题抽取、原始附件/结果表区分、结果解释软映射、轻依赖脚手架、报告拼装 raw-data 标记与回归验证口径。
- `references/llm-wiki-mathematical-modeling-agent-page.md`：将数学建模智能体灌入用户 LLM Wiki 时的页面边界和推荐页面清单；强调 wiki 记录概念地图，skill 保留操作手册与脚本。

## 触发场景

当用户要求完成以下任务时加载本技能：

- 数学建模竞赛：MCM/ICM、美赛、国赛、校赛、课程建模题。
- 开放性现实问题建模：优化、预测、评价、仿真、调度、路径规划、资源配置、风险评估。
- 需要从题目与数据出发，产出模型、Python 求解代码、图表、论文/报告/答辩材料。
- 用户说“数学建模智能体”“建模 Agent”“帮我做建模题”“写建模论文/报告”。
- 用户说“继续优化数学建模智能体/继续优化”时，默认不是解释下一步，而是按 `references/continuous-optimization-notes.md` 的优先级继续落地一个可运行闭环组件；优先增强自动化、审计、状态推进、pipeline 编排，而不是继续堆模型名。
- 用户说“真正打比赛/能获奖/正式比赛拿到题后更好完成比赛”时，默认优化对象是**通用数学建模智能体能力**，历史题只是测试 fixture；不要把工作重心变成继续专项硬编码某一道旧题，除非用户明确要求做该题正式解。

## 核心原则

1. **先读题再建模**：不得没读清目标、约束、数据字段就直接套模型。
2. **模型服务问题**：不要为了高级而高级；优先选择能解释、能运行、能验证的模型。
3. **全链路可复现**：题目解析、数据清洗、公式、代码、图表、结果解释必须能互相对上。
   - 真实国赛/校赛附件常是 Excel：默认数据审计与 baseline 不得只扫描 CSV，应支持 `*.xlsx` 多 sheet 审计与数值摘要。
   - 遇到价格区间如 `2.50-4.00` 时，轻量 baseline 可用区间中点做 sanity summary，但必须标注这不是正式模型参数估计。
4. **假设显式化**：所有简化、忽略项、边界条件都要写成可审查的模型假设。
5. **代码必须真实运行**：有数据时必须运行 Python/求解器验证结果，不得只写伪结果。
6. **报告不是堆砌**：论文/报告必须围绕问题、模型、结果、敏感性和局限性组织。

## 标准八段式中间表示

每道建模题都转化为以下中间表示：

1. **目标**：题目到底要求优化/预测/评价/解释什么？输出指标是什么？
2. **对象与系统边界**：研究对象、时间范围、空间范围、参与主体、外部条件。
3. **变量**：决策变量、状态变量、输入变量、输出变量、参数。
4. **约束**：物理约束、资源约束、逻辑约束、时间约束、数据约束。
5. **假设**：为什么可以简化？假设对结果有什么影响？
6. **方法**：候选模型、选择理由、公式结构、求解算法。
7. **验证**：数据验证、代码运行、误差分析、敏感性分析、鲁棒性检查。
8. **报告**：摘要、问题重述、假设、符号、模型建立、求解、结果、检验、优缺点。

## 工作流

### 0. 历史题复跑 / 技能诊断 Rerun Evaluation

当用户要求“复跑以前做过的建模题”“拿旧题测试技能”“检查并优化数学建模智能体”时，先读取 `references/rerun-evaluation-protocol.md`。

这类任务的默认目标不是重做出一个更漂亮的旧答案，而是诊断智能体能力：材料定位、附件审计、题意重建、模型口径、代码复现、差异解释、报告一致性和技能补丁。

必须先区分复跑目标：

- **技能诊断**：重点输出缺陷清单、流程补丁、新增门禁/模板/脚本。
- **正式复现**：重点找齐原始附件并尽量复现旧结果。
- **论文重写**：重点改模型表达、图表、报告结构。
- **模型升级**：重点替换或增强算法，并清楚区分新旧模型。

如果输入附件不完整或使用重构数据，数值结果只能作为链路测试，不能作为正式结论。最终回复应优先汇报“技能优化了什么”。

### 1. 题目解析 Problem Analysis

先按小问读取 `references/problem-type-routing.md` 做题型路由。若题目涉及医学检测、疾病筛查、NIPT、重复测量、阈值达标时间，必须同时读取 `references/biostatistics-and-screening.md`。若是比赛多题选题，先读取 `references/topic-selection-rubric.md`。若存在历史相似题，先读取 `references/case-study-index.md` 选择相关案例。

输出 `problem_analysis.md` 或在回复中给出：

- 背景概括：一句话说明现实场景。
- 任务清单：逐条拆出题目中的子问题。
- 数据清单：有哪些附件/字段/单位/时间跨度/缺失风险。
- 输出要求：每问需要的最终答案、图表、指标或建议。
- 隐含约束：现实可行性、政策/物理/经济限制。
- 评分点猜测：建模合理性、结果可信度、创新性、论文表达。

### 2. 子任务拆解 Problem Decomposition

将问题拆成可执行子任务，并建立依赖 DAG：

```text
Task 1: 数据理解与预处理
Task 2: 指标体系/变量构造
Task 3: 核心模型 A
Task 4: 核心模型 B 或优化/预测
Task 5: 敏感性/鲁棒性分析
Task 6: 论文整合与图表解释
```

对每个子任务记录：

- 输入：题目文本、数据、上游结果。
- 输出：表格、参数、图、模型结果、结论。
- 依赖：依赖哪些前置任务。
- 验证：如何判断该任务完成。

### 3. 方法检索 HMML-style Method Retrieval

按“问题类型 → 子类型 → 方法”选择模型。优先给出 2–4 个候选，再说明取舍。

#### 优化类

- 线性规划 LP：资源分配、生产计划、运输调度。
- 整数规划 IP / 混合整数规划 MIP：选址、路径、排班、0-1 决策。
- 非线性规划 NLP：非线性收益/成本、连续优化。
- 多目标规划：成本、时间、风险、碳排等冲突目标。
- 动态规划：阶段决策、库存、路径、资源分配。
- 网络流/最短路/最大流：交通、物流、通信网络。
- VRP/TSP：车辆路径、配送、旅行路线，必要时接入 `vrp-solver`。

#### 预测类

- 回归模型：线性/岭/Lasso/多项式回归。
- 时间序列：ARIMA/SARIMA/指数平滑/Prophet 类思路。
- 机器学习：随机森林、XGBoost/LightGBM、SVR、神经网络。
- 灰色预测 GM(1,1)：小样本趋势预测。
- Markov/状态转移：状态演化、风险等级迁移。

#### 评价类

- AHP：主观权重、层次指标体系。
- 熵权法：客观权重、指标离散度。
- TOPSIS：多指标综合排序。
- 模糊综合评价：模糊等级与主观判断。
- PCA/因子分析：降维、综合指标。

#### 统计与因果类

- 假设检验、置信区间、方差分析。
- 相关/偏相关/回归诊断。
- 面板数据、DID、倾向得分匹配：仅在数据条件满足时使用。

#### 仿真类

- Monte Carlo：不确定性传播、风险估计。
- 系统动力学：反馈系统、库存流量。
- 排队论：服务系统、等待时间。
- 元胞自动机/Agent-based Simulation：空间扩散、人群行为。

#### 图与网络类

- 图中心性、社区发现、连通性。
- 最短路径、最小生成树、最大流。
- 复杂网络鲁棒性分析。

### 4. 数学建模 Mathematical Modeling

每个模型至少包含：

```text
变量定义：x_i, y_t, p_j 等
参数定义：c_i, d_i, capacity_i 等
目标函数：min/max ...
约束条件：s.t. ...
求解方法：解析解/数值优化/启发式/仿真
选择理由：为什么该模型适合本题
```

建模时检查：

- 变量单位是否一致。
- 目标函数是否真正对应题目目标。
- 约束是否可行，不互相矛盾。
- 数据是否足以支撑模型参数估计。
- 如果模型复杂，是否有基线模型作对照。

### 5. 计算求解 Computational Solving

有数据时默认创建可运行 Python 脚本：

```text
src/
  preprocess.py
  model.py
  solve.py
  sensitivity.py
results/
  tables/
  figures/
  logs/
report/
  report.md / report.docx / report.pdf
```

代码要求：

- 使用 `pandas/numpy/scipy/sklearn/matplotlib` 等常规库。
- 求解优化问题时优先使用可安装性高的 `scipy.optimize`、`pulp`、`ortools`、`cvxpy`，根据环境选择。
- 每个关键结果保存到 `results/`。
- 图表必须有标题、坐标轴、单位、图注。
- 随机过程固定 seed。
- 输出日志包含运行时间、样本量、关键参数。

### 6. 验证与迭代 Verification

复杂项目按 `references/project-state-machine.md` 管理 S0-S8 状态；每次宣称完成必须有文件路径或可验证产物。终稿前必须读取 `references/report-consistency-checklist.md`。遇到异常、赶工或模型选择不确定时，读取 `references/modeling-failure-patterns.md` 排雷。

最低验证清单：

- 数据行列数、缺失值、异常值检查。
- 核心公式与代码变量对应。
- 至少一个 baseline 或 sanity check。
- 参数敏感性分析：扰动关键参数 ±5%、±10%、±20%。
- 鲁棒性分析：替换权重、替换模型或交叉验证。
- 结果可解释性：是否符合常识和题目背景。
- 如果结果异常，优先检查数据、单位、约束和代码，而不是强行解释。
- 如果存在同一主体多次观测，显著性检验和机器学习划分必须考虑主体内相关，不能默认所有行独立。
- 如果任务是异常判定/医学筛查，必须做数据泄漏检查，不能只报告 Accuracy。

### 7. 报告/论文生成 Solution Reporting

数学建模论文推荐结构：

1. 摘要：问题、方法、核心结果、结论，避免空话。
2. 问题重述：背景与各问目标。
3. 模型假设：编号列出，并解释合理性。
4. 符号说明：变量、参数、单位。
5. 数据处理：来源、清洗、描述统计、可视化。
6. 模型建立与求解：逐问组织，不要模型和结果脱节。
7. 模型检验：误差、敏感性、鲁棒性。
8. 结果分析与建议：直接回答题目。
9. 模型优缺点：真实、具体，不写套话。
10. 参考文献与附录：代码、表格、额外图。

若用户要求课程报告/DOCX，结合本机公文/DOCX 规范或 `Word / DOCX` 技能生成正式文件。

## 与 Hermes 工具配合

- `read_file/search_files`：读取题目、附件说明、已有代码。
- `terminal/execute_code`：运行 Python、统计数据、生成图表。
- `web_search/web_extract`：查公开背景、政策、文献，但必须标注来源。
- `viking_search/viking_read`：检索用户历史建模材料、论文库、课程资料。
- `skill_view('vrp-solver')`：绿色物流、VRP、路径规划类问题优先加载；如果记忆中出现旧名 `green-logistics-vrp`，先用 `skills_list(category='data-science')` 查验真实技能名。
- `skill_view('Word / DOCX')` 或 DOCX/PDF 相关技能：生成正式报告。
- `scripts/create_modeling_project.py`：创建标准数学建模项目目录。
- `scripts/finalize_modeling_project.py`：生成最终提交包、README_submit.md、submission_manifest.json 与 SHA256SUMS.txt。
- `scripts/audit_report_consistency.py`：提交前自动审计报告源文件与结果表、图表、关键数值、单位的一致性。
- `scripts/update_project_state.py`：自动推进 S0-S8 状态并写回 PROJECT_STATE.md/project_meta.json。
- `scripts/modeling_pipeline.py`：一条命令串联数据审计、质量门禁、报告一致性审计、状态推进、最终打包和总控摘要。
- `scripts/quality_gate_plus.py`：增强质量门禁，用于终稿前检查结果表非空、baseline/core/sensitivity 证据、报告逐问痕迹和状态一致性。
- `scripts/problem_coverage_tracker.py`：问题小问覆盖追踪器，用于从题目解析抽取小问并检查报告、结果表、图表是否逐问覆盖。
- `scripts/result_interpretation_helper.py`：模型结果解释生成器，用于从核心结果表、敏感性分析和图表生成逐问解释草稿。
- `scripts/report_section_assembler.py`：证据优先报告拼装器，用于把逐问解释草稿、结果表、图表和风险提示拼成可编辑报告骨架。
- `scripts/repair_advisor.py`：修复建议器，用于把各类审计结果汇总成优先级修复清单和交付 readiness 判断。
- `scripts/competition_readiness_gate.py`：竞赛就绪度门禁，用于区分工程闭环、正式模型、可参赛冲奖三个层级；真实比赛/冲奖目标下应作为最终门禁之一。
- `scripts/competition_evidence_builder.py`：竞赛证据自动汇总器，用于把项目产物自动整理为 `competition_evidence.json`，供就绪度门禁和人工复盘使用。
- `scripts/contest_qc_gate.py`：竞赛质控门禁。新项目先用 `--init --phase early` 建立登记表；主模型、真实附件 PoC 和正式运行完成后用 `--phase model`；终稿前用 `--phase final`。它验证真实数据 PoC、模型交接、数学检查、可复现 run、结果/主张/图表映射、P0/P1 风险和提交合规，`final_ready` 不等于获奖保证。
- `scripts/contest_evidence_sync.py`：在 Contest QC 前同步 `deliverable_matrix.csv`、`result_registry.csv` 和 `figure_evidence.csv` 的待审核候选。可先运行 `--dry-run`；同步器不生成 `passed`、`checked` 或 `paper_ready`，冲突与 schema 异常必须先修复。
- `scripts/model_skeleton_router.py`：题型路由后的模型骨架生成器，用于拿到题后尽快形成“题型→变量→目标/指标→约束/checker→验证资产”的可执行起点。
- `scripts/domain_checker_template_builder.py`：领域 checker 模板库，用于把路由结果转成可执行 checker 起点；生成模板不等于正式约束验证，必须替换 TODO 后才可作为 model_ready 证据。
- `references/automation-workflow.md`：闭环执行器规范；当用户说“继续优化技能/让它自动跑起来/做成项目闭环”时读取。
- `references/case-study-cumcm-2024-c-crop-strategy-20260523.md`：当用户说“真正打比赛/能获奖/冲奖/国赛题测试”时参考。此类任务默认进入竞赛级模式：不能满足于 S0-S8 文件闭环；必须构造题目特定模型或求解器、填写官方结果模板、运行领域约束 checker，并明确区分“轻量闭环 / 可行启发式 MVP / 精确优化 / 冲奖级论文”。
- `references/report-result-audit-design.md`：报告-结果自动审计设计；当下一步要实现 `audit_report_consistency.py` 或检查报告数值、图表、表格、提交包一致性时读取。
- 严格提交前检查中，如果结果目录存在 baseline/sensitivity/中间结果表但报告未引用，默认视为有效风险信号：要么在报告/附录中显式引用并解释，要么从最终交付结果目录中排除，不能让未解释旧表混入提交包。

## 产物约定

推荐目录：

```text
~/Documents/数学建模/<项目名>/
  problem/
  data/
  src/
  results/
    figures/
    tables/
  report/
  README.md
```

关键产物：

- `problem_analysis.md`：题目解析与任务拆解。
- `model_design.md`：模型假设、变量、公式、方法选择。
- `solve.py` 或 `notebook.ipynb`：可运行求解代码。
- `results_summary.md`：结果与验证摘要。
- `report.docx` / `report.pdf`：最终报告。

## 质量门禁

完成前必须确认：

- [ ] 每个题目小问都有明确回答。
- [ ] 模型假设、变量、公式、代码一致。
- [ ] 代码真实运行，关键结果不是编造。
- [ ] 图表编号连续，正文有引用和解释。
- [ ] 做过至少一种敏感性/鲁棒性验证。
- [ ] 报告结论直接对应题目要求。
- [ ] 不夸大模型精度，不隐藏数据不足。
- [ ] 若任务是历史题复跑，最终输出必须优先说明技能诊断发现、已做技能补丁、下次流程如何改进；数值复跑结果只能作为证据或链路测试，不得喧宾夺主。
- [ ] 若真实题测试只跑通轻量 baseline/placeholder 模型，必须明确区分“S0-S8 工程闭环完成”和“正式最优解完成”；不得把 `recommended_status=completed` 解释为国赛答案可提交。
- [ ] 真实比赛/冲奖目标下，终稿前必须先运行 `contest_qc_gate.py --phase final`：任何真实附件 PoC、模型交接、数学核验、可复现 run、主张/图表证据、P0/P1 风险或当前官方规则/匿名/AI 披露缺口都不能被润色掩盖；只有 `final_ready` 才表示该证据层通过。
- [ ] 自动同步产生的 `candidate` 只能作为待审核线索；不得仅因文件存在将其手工批量改为 `provided`、`checked` 或 `paper_ready`。
- [ ] 真实比赛/冲奖目标下，最终必须运行 `competition_readiness_gate.py`；只有 `competition_ready=true` 才能称为达到可参赛评审口径，且仍不得承诺必然获奖。
- [ ] 若用户纠正“任务目的/工作流/输出重心”，立即把纠正沉淀到本技能或相应 reference，而不是只在当前回复中道歉。
- [ ] 当用户说“找一个真实竞赛题跑一轮端到端闭环”且上下文涉及数学建模智能体时，默认必须使用 `mathematical-modeling-agent` 的项目脚手架、S0-S8 状态机、Pipeline、质量门禁和提交包流程；不要误转到 `~/software-agent`，除非用户明确说软件智能体。

## 从 MM-Agent 吸收的思想

本技能吸收的是公开项目 `usail-hkust/LLM-MM-Agent` 的方法论层思想，而不是复制其源码：

- 四阶段流程：问题分析 → 数学建模 → 计算求解 → 结果报告。
- 子任务拆解与依赖 DAG。
- HMML 分层建模方法库检索。
- Actor/Critic 式模型方案自检与改进。
- 代码生成、运行、调试、解释闭环。

注意：该项目 GitHub 页面存在 CC BY-NC、GPLv3、Non-Commercial Use 等许可表述差异。用于本地学习和技能化方法论可以；若要复制源码、部署服务或商业使用，必须先做许可证审查并取得必要许可。
