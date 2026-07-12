# Session learning: competition-grade modeling agent upgrades (2026-05-23)

## Durable lesson

When the user says the mathematical modeling agent should “真正打比赛 / 能获奖 / 继续优化”, the target is not a single historical problem. Treat old CUMCM/MCM problems as fixtures to expose reusable weaknesses in the class-level workflow.

The correct optimization axis is a competition quality-control and production chain:

```text
problem_analysis
→ model_skeleton routing
→ domain checker templates
→ problem-specific model implementation
→ formal checker issue_count=0
→ competition_evidence
→ competition_readiness
→ report/submission package
```

## Components added in this session

### 1. `model_skeleton_router.py`

Purpose: turn `06_过程记录/problem_analysis.md` into a typed model skeleton.

Outputs:

```text
06_过程记录/model_skeleton/model_skeleton.json
06_过程记录/model_skeleton/model_skeleton.md
02_代码/generated_skeleton/*.py  # optional with --write-code
```

Pipeline position:

```text
data_audit → model_skeleton → domain_checker_templates → quality_gate
```

Important boundary: `model_skeleton` is only a route/start point; it is not `model_ready`.

### 2. `domain_checker_template_builder.py`

Purpose: generate checker starters from routed problem types.

Outputs:

```text
06_过程记录/领域checker/domain_checker_templates.json
06_过程记录/领域checker/domain_checker_templates.md
02_代码/generated_checkers/check_<type>.py
```

Covered types: optimization, network_routing, prediction, evaluation, simulation, statistics, unknown.

Important boundary: generated checker templates are not formal checker evidence. Their TODO/warn checks must be replaced with project-specific assertions over formal result tables/parameters.

### 3. `competition_evidence_builder.py` checker-status hardening

Purpose: prevent template checker artifacts from being mistaken for formal model evidence.

`domain_checker.implementation.status` now distinguishes:

```text
not_detected
checker_detected_no_machine_output
template_checker_only
implemented_checker_warn
implemented_checker_fail
implemented_checker_pass
```

Only `implemented_checker_pass` should allow `domain_checker.status=pass`.

Formal pass requires:

```text
checker output exists
issue_count=0
warn_count=0
no TODO/template/starter residue
```

## Execution discipline learned

For this class of skill-maintenance task, every “继续” should land one verified component, not more planning prose:

1. inspect current skill/components;
2. implement scripts/references/templates;
3. wire into scaffold and pipeline;
4. py_compile changed scripts;
5. run a minimal project fixture;
6. clean `__pycache__` to `~/.Trash`;
7. update SKILL.md and continuous notes.

## Pitfall

Do not let early-stage pipeline modes run terminal gates that require reports/results. Add early-stage modes such as `--skeleton-only` so the first-hour competition workflow can validate routing/checker scaffolding without false failures from final-delivery gates.
