# Contest QC Integration Audit — 2026-07-11

## Trigger

Use when evaluating or extending the umbrella skill's competition-grade evidence and readiness workflow. This is an implementation-audit reference, not a requirement to create a multi-skill suite.

## Durable finding

The skill already contains `scripts/contest_qc_gate.py`: a compact executable evidence gate with 13 registries under `06_过程记录/竞赛质控/` and `early`, `model`, `final` phases. Prefer wiring and hardening this single gate over importing the candidate suite's 17 role-specific skills.

Core registries already covered:

- scope/model: `deliverable_matrix.csv`, `symbol_table.csv`, `assumption_log.csv`, `model_handoff.md`;
- execution: `poc_registry.csv`, `math_verification.csv`, `run_record.csv`, `artifact_manifest.csv`, `result_registry.csv`, `figure_evidence.csv`;
- paper/final: `claim_ledger.csv`, `consistency_audit.csv`, `review_findings.csv`, `review_pass_items.csv`, `submission_checklist.md`.

## Integration checklist

1. Scaffold a `02_代码/17_contest_qc.py` wrapper and initialize the QC directory non-destructively for new projects.
2. Link the gate in README, `project_meta.json`, SKILL instructions, and the control pipeline.
3. Have `competition_readiness_gate.py` consume `contest_qc_gate.json`: QC `blocked` must prevent a competition-ready verdict; missing QC can be a migration warning unless strict mode is requested.
4. Keep `competition_evidence_builder.py` as heuristic discovery/placeholder warning only. It must not replace registry-based evidence checks.
5. Run `early` to lock problem/deliverables, `model` after traceable PoC/formal runs, and `final` before packaging. Do not describe `model` as a pre-code gate while it requires completed outputs.

## Implemented hardening

The integration now enforces these deterministic checks:

- `accepted_omission` requires `approval_source`, `omission_reason`, and `accepted_by`.
- `result_registry.csv` and `figure_evidence.csv` carry `deliverable_id`; each `provided` deliverable must have paper-ready result or figure evidence at final gate.
- A formal run requires `run_status=completed` and an existing `entry_script`; result evidence requires an existing source table and source script plus a completed `run_id`.
- A paper-ready figure requires run linkage, caption, post-figure conclusion, existing figure path, and render or human visual pass.
- Open P0/P1 review findings, failed/blocked mathematical checks, open high-risk consistency rows, unsupported paper claims, or missing current rule/anonymity/reproducibility/AI-disclosure state block `final_ready`.
- `competition_readiness_gate.as_bool()` treats an explicit false/template/warn status as authoritative; non-empty paths or metadata cannot upgrade it to pass.
- `--freeze-run` hashes a completed run's declared entry, inputs, result tables, and figures without executing its command. Final QC fails closed when the manifest is absent, malformed, stale, or inconsistent with paper-ready result/figure linkage.

## Remaining boundary

`model_handoff.md` is intentionally a compact semantic check (required sections plus non-template content), not a proof that the model is mathematically correct. Header/enum validation can be tightened in a future schema version only when it does not reject legitimate contest-specific extensions.

## Regression tests

Use temp-project fixtures to test: scaffold creates wrappers/registries; early lock pass; missing real-data PoC or broken script/run/result reference blocks model phase; unsupported paper claim/P1/compliance gap blocks final phase; a complete minimal fixture passes; entry/input/table/figure hash drift blocks final phase; explicit non-pass evidence cannot bypass readiness; pipeline and readiness cannot bypass QC `blocked`.

## Candidate-suite triage lessons

Do not import an entire role suite merely because its artifact schema is strong. The candidate's reusable value was the evidence contract, while its project runner and visual defaults were not production-ready: its root reproducer referenced nonexistent `q1/src/compute.py`, and its default generated PNG was about 220 DPI although its own strict figure checker required 300 DPI. Treat reusable template assets as fixtures that require end-to-end tests.
