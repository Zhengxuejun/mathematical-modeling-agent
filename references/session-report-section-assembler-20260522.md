# 会话沉淀：report_section_assembler 证据优先报告拼装器（2026-05-22）

## 背景

本轮连续优化 `mathematical-modeling-agent` 时，已在问题覆盖追踪器和结果解释生成器之后，新增证据优先报告拼装器：

```text
scripts/report_section_assembler.py
references/report-section-assembler.md
```

目标不是自动生成终稿，而是把每个小问稳定拼成可编辑报告骨架，强制包含：

```text
直接结论 → 模型与方法 → 证据表 → 图表解释 → 敏感性/鲁棒性/局限性
```

## 落地内容

新增脚本输出：

```text
05_报告定稿/report_draft.md
06_过程记录/报告拼装/report_section_assembly.md
06_过程记录/报告拼装/report_section_assembly.json
```

项目脚手架新增：

```text
06_过程记录/报告拼装/
02_代码/11_report_assembler.py
project_meta.json: report_section_assembler
```

Pipeline 新增步骤：

```text
problem_coverage
→ result_interpretation
→ report_assembly
```

Pipeline 参数：

```bash
--skip-report-assembly
--strict-report-assembly
--report-title "数学建模报告"
--report-draft-name report_draft.md
```

## 关键实现原则

1. **证据优先，不冒充终稿**  
   直接结论、模型与方法等段落保留 `待编辑`，脚本只负责把已有证据组织到正确位置。

2. **逐问章节必须结构化**  
   每个小问固定生成五段，避免报告只堆模型和图表但漏答题目。

3. **表格/图表匹配优先用上游解释草稿**  
   优先读取 `result_interpretation_draft.json`；如果不存在，再回退到 `problem_coverage.json` 或 `problem_analysis.md`。

4. **不要硬编码不存在的结果表引用**  
   初版曾在数据处理章节写入反引号形式的 `03_结果表格/data_audit.csv`，当测试项目没有该文件时，被 `audit_report_consistency.py` 识别成不存在的结果表 token（如 `dataaudit`），导致 Pipeline 失败。修复口径：报告骨架只能写“建议引用数据审计结果表”，不要用反引号硬写未确认存在的文件名。

5. **严格模式用于终稿前，而不是早期草稿**  
   `--strict` 在存在 partial/weak 章节或全局风险时返回非零，适合终稿前卡门禁；早期建模阶段可以先普通模式生成骨架。

## 验证结果

### 单脚本验证

测试项目：

```text
~/test/math_modeling_skill_report_assembler_verify/report_assembler_case
```

结果：

```text
Questions: 3
ready=3
partial=0
weak=0
fail=0
warn=0
```

### Pipeline 集成验证

测试项目：

```text
~/test/math_modeling_skill_report_assembler_pipeline_verify/pipeline_report_case
```

结果：

```text
Recommended status: completed
Highest contiguous state: S8
报告骨架拼装：questions=3 ready=3 partial=0 weak=0 warn=0 fail=0
```

## 后续方向

下一步最有价值的是 `repair_advisor.py`：读取 quality_gate_plus、problem_coverage、result_interpretation、report_section_assembly、auto_report_audit 和 pipeline 摘要，输出“能不能交、还差什么、先修哪里”的优先级修复清单。
