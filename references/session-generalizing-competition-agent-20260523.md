# Session: Generalizing the Mathematical Modeling Agent for Competition Readiness (2026-05-23)

## Trigger

User corrected the direction of work after a real CUMCM 2024 C rerun: the goal is **not** to overfit one historical problem, but to improve the **general mathematical-modeling agent** so that during an actual contest it can handle newly released problems better and have award-level potential.

Key user correction:

> “我们要优化的是通用型的数学建模智能体，而不是只针对这一个题目，到正式比赛的时候，拿到题目后能更好完成比赛。”

## Durable workflow lesson

Historical problems should be treated as **test fixtures**, not as the optimization target. A real-problem rerun is valuable only insofar as it reveals reusable defects in the agent’s competition workflow.

When a user says “能真正打比赛 / 能获奖 / 正式比赛拿到题目后能做好”, do not keep specializing the last test problem. Instead improve general capabilities:

1. problem-type routing;
2. model scaffold generation;
3. domain-specific checker generation;
4. evidence collection;
5. competition readiness gates;
6. paper-asset and report-quality gates.

## Implemented general upgrades in this session

### 1. Competition readiness gate

Added generic readiness gate:

```text
scripts/competition_readiness_gate.py
references/competition-readiness-gate.md
```

Purpose: separate three levels that were previously conflated:

```text
workflow_ready      # project artifacts/pipeline closed
model_ready         # real problem-specific model, no placeholder, checker evidence
competition_ready   # per-question coverage, comparison, sensitivity/robustness/risk analysis, paper assets, consistency
```

Important expression rule: `S0-S8 completed` or `recommended_status=completed` must not be described as contest-ready unless `competition_ready=true` or the remaining gaps are explicitly disclosed.

### 2. Competition evidence builder

Added evidence aggregation before readiness judging:

```text
scripts/competition_evidence_builder.py
references/competition-evidence-builder.md
```

It writes:

```text
06_过程记录/competition_evidence.json
06_过程记录/competition_evidence.md
```

It summarizes:

- artifact counts;
- placeholder/TODO/link-test remnants;
- problem-specific model evidence;
- domain checker and issue_count evidence;
- official result/template outputs;
- optimization solver evidence;
- simulation/risk evidence;
- model comparison;
- sensitivity/robustness;
- paper assets;
- upstream audit/readiness summaries.

Pipeline order should be:

```text
repair_advisor → competition_evidence → competition_readiness
```

## Validation lesson from CUMCM 2024 C fixture

Running the new gates on the 2024C project correctly produced:

```text
workflow_ready=True
model_ready=False
competition_ready=False
readiness=model_not_ready
```

This was desirable because the project had real artifacts and checker evidence, but still retained placeholder/link-test semantics and insufficient paper assets. The gate therefore prevented a false “ready to compete” claim.

## Future optimization priority

The next high-leverage component should be a **problem-type-routed model scaffold generator**:

Input:

```text
06_过程记录/problem_analysis.md
```

Output, depending on detected problem class:

```text
06_过程记录/model_design.md
02_代码/03_model_main.py
02_代码/check_constraints.py
02_代码/04_sensitivity.py
06_过程记录/competition_evidence.json initial template
```

The generator should support at least:

- optimization / allocation / scheduling;
- prediction / regression / time series;
- evaluation / ranking / weighting;
- simulation / uncertainty;
- routing / network / graph;
- statistical testing / causal or screening-style tasks.

## Pitfall to avoid

Do not interpret a real historical problem’s custom solver as the final answer to “optimize the agent.” A custom solver can be a useful fixture, but the durable improvement must be promoted into class-level scripts, templates, checks, or references under this skill.
