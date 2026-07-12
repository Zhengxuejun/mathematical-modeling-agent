# LLM Wiki page for mathematical modeling agent (2026-05-23)

## Why this belongs in the LLM Wiki

The mathematical modeling agent is a class-level workflow, not a one-session artifact. It should be represented in the user’s LLM Wiki as an entity/workflow map because it has stable structure across tasks:

- problem analysis;
- subtask DAG;
- HMML-style method retrieval;
- mathematical modeling;
- computational solving;
- report generation;
- S0-S8 project state machine;
- problem coverage tracking;
- result interpretation;
- report assembly;
- report-result audit;
- repair advisor;
- competition readiness gate.

The skill remains the operational source of truth for scripts and exact execution steps. The wiki page should be a conceptual map and boundary document.

## Recommended wiki pages

When seeding or updating the LLM Wiki for mathematical modeling, prefer these pages:

- `entities/mathematical-modeling-agent.md` — overall entity/workflow map.
- `concepts/modeling-s0-s8-state-machine.md` — project state machine.
- `concepts/model-skeleton-router.md` — route problem analysis into model skeleton and starter checkers.
- `concepts/competition-readiness-gate.md` — distinguish workflow/model/competition readiness.
- `concepts/problem-coverage-tracker.md` — prevent missing subquestions.
- `concepts/result-interpretation-helper.md` — generate per-question interpretation drafts.
- `concepts/report-section-assembler.md` — evidence-first report skeleton.
- `concepts/report-result-audit.md` — report/result/figure/submission consistency.
- `concepts/repair-advisor.md` — aggregate failures/warnings into prioritized fixes.

## Boundary to encode

Important text to preserve in the wiki:

> When the user says “数学建模智能体”, “建模 Agent”, “真正打比赛”, “能获奖”, or asks for a modeling competition end-to-end loop, prefer the mathematical-modeling-agent workflow rather than routing to generic software-agent, unless the user explicitly says software-agent.

## What not to put in the wiki

Do not copy full scripts or long reference files into the wiki. Keep those inside this skill. The wiki should point to concepts and summarize why they matter.

Do not store one-off run IDs, transient task progress, or temporary competition outputs in the wiki. If a historical case contains durable lessons, create or update a case-study page with stable failure patterns and reusable lessons.
