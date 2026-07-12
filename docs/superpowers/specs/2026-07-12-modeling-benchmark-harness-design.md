# Modeling Benchmark Harness Design

Date: 2026-07-12
Status: design ready for user review

## Goal

Add a deterministic, offline benchmark harness that measures whether a generated
mathematical-modeling submission is correct, feasible, statistically defensible,
reproducible, evidence-consistent, and reasonably efficient. The required CI
benchmark must run without an LLM API, network access, or hidden mutable state.

## Why This Is The Next Capability

The repository's current tests verify workflow components, evidence gates, and
packaging behavior. They do not produce a comparable capability score across
modeling problem types. A benchmark contract makes future improvements
measurable and prevents a change from improving report completeness while
silently weakening mathematics, statistics, or reproducibility.

## Non-goals

- Do not claim that three microcases predict competition awards.
- Do not execute an autonomous LLM agent in required CI.
- Do not bundle copyrighted contest statements or official attachments.
- Do not use an LLM judge for required scores.
- Do not grade writing style, novelty, or domain insight in v1.
- Do not make benchmark scores part of `competition_ready` for user projects.

## User Workflow

Run one submission against one case:

```bash
python scripts/modeling_benchmark.py run \
  --case benchmarks/cases/optimization_capacity \
  --submission /path/to/submission
```

Run the bundled reference suite:

```bash
python scripts/modeling_benchmark.py suite --fixtures benchmarks/fixtures
```

Validate case definitions without grading submissions:

```bash
python scripts/modeling_benchmark.py validate --cases benchmarks/cases
```

`run` writes results under the submission's
`06_过程记录/benchmark/`. `suite` writes an aggregate report under
`benchmark-results/` or a caller-provided output directory. Required CI uses
temporary directories so repository state remains clean.

## Case Contract

Each case is a directory:

```text
benchmarks/cases/<case_id>/
  case.json
  input/
  expected.json
```

`case.json` is public and contains:

- schema version and stable case ID;
- category and difficulty;
- submission file requirements;
- metric definitions, weights, tolerances, and directions;
- hard-block rules;
- efficiency budget;
- input-file inventory and SHA-256 values.

`expected.json` contains deterministic ground truth and grader parameters. It is
kept separate so a future live-agent runner can expose only `case.json` and
`input/` during execution. Required CI may read it directly.

The schema rejects unknown scoring dimensions, negative weights, weights that
do not sum to 1, unsafe relative paths, duplicate rule IDs, invalid tolerances,
and input hash mismatches. Case paths cannot escape the case directory through
absolute paths, `..`, or symlinks.

## Submission Contract

V1 grades a small, explicit artifact contract instead of heuristically reading
arbitrary reports:

```text
submission/
  solution.json
  run_record.json
  report.md
  artifacts/
```

`solution.json` contains case-specific outputs plus common metadata:

- `case_id`;
- `model_name` and `model_version`;
- `random_seed`;
- `metrics` mapping string names to finite numbers;
- `checks` mapping named constraints/validity checks to booleans or finite values;
- `evidence` mapping claims to project-relative artifact paths.

`run_record.json` contains the entry command, input hashes, runtime seconds,
exit code, and generated artifact inventory. The grader never treats a claimed
path as evidence unless it resolves inside the submission, exists, and matches
the declared SHA-256 when a hash is required.

## Scoring Model

Every case uses the same six dimensions, with case-specific rule weights inside
each dimension:

| Dimension | Suite weight | Meaning |
|---|---:|---|
| correctness | 0.30 | Required values, decisions, rankings, or predictions match deterministic expectations within tolerance |
| feasibility | 0.20 | Hard constraints, domains, conservation rules, and residual bounds hold |
| statistical_validity | 0.15 | Split design, uncertainty, test assumptions, leakage checks, or stability evidence are appropriate |
| reproducibility | 0.15 | Seed, command, input hashes, exit status, and required artifacts form a replayable record |
| evidence_consistency | 0.10 | Report claims and declared evidence agree with machine-readable outputs |
| efficiency | 0.10 | Runtime stays within the case budget without affecting mathematical correctness |

Each rule returns `pass`, `partial`, or `fail`, a normalized score in `[0, 1]`,
and machine-readable evidence. Dimension scores are weighted means. The total is
the weighted sum on a 0-100 scale before hard-block caps.

### Hard Blocks

Hard blocks are deterministic facts, not heuristic warnings:

- an infeasible optimization decision;
- target leakage explicitly detected by the case grader;
- non-finite or fabricated required metrics;
- case/input hash mismatch;
- a claimed run with non-zero exit code;
- missing mandatory machine-readable solution output.

An integrity hard block sets total score to 0. A mathematical/statistical hard
block caps total score at 49.99 and sets verdict `blocked`. This preserves
diagnostic dimension scores while preventing a polished but invalid submission
from receiving a passing verdict.

Verdicts are:

```text
invalid   submission/case contract cannot be trusted; score 0
blocked   contract is readable but a mathematical/statistical hard block exists
needs_work total score below 70 with no hard block
pass      total score at least 70, no hard block, every core dimension at least 0.50
strong    total score at least 85, no hard block, every core dimension at least 0.75
```

Core dimensions are correctness, feasibility, statistical validity, and
reproducibility.

## Initial Cases

### 1. `optimization_capacity`

A small integer resource-allocation problem with known optimum. It checks
decision integrality, capacity and demand residuals, objective recomputation,
baseline comparison, input provenance, and runtime. A plausible low-cost but
infeasible solution must be blocked.

### 2. `prediction_group_leakage`

A seeded grouped prediction dataset in which rows from the same entity repeat.
It checks group-aware splitting, absence of target/future leakage, prediction
error, uncertainty or fold variability, seed recording, and report consistency.
A high score produced with row-random leakage must be blocked.

### 3. `evaluation_rank_stability`

A deterministic multi-criteria evaluation problem. It checks indicator
direction normalization, weight sum, expected ranking, perturbation stability,
tie handling, and evidence for the reported recommendation. A correct base rank
without required stability analysis receives partial statistical-validity
credit rather than a hard block.

Input data is generated and committed as small text/CSV fixtures. The case
descriptions capture real competition failure patterns without copying official
problem text or attachments.

## Architecture

Add focused modules under `scripts/benchmark/`:

- `contracts.py`: typed case, submission, rule, and result models plus schema validation;
- `paths.py`: project-local path and hash validation;
- `rules.py`: reusable exact, tolerance, boolean, residual, ranking, evidence, and budget rules;
- `grader.py`: case loading, rule execution, hard-block application, and verdict calculation;
- `reporting.py`: deterministic JSON and Markdown output;
- `suite.py`: reference-fixture discovery and aggregate scoring;
- `modeling_benchmark.py`: small CLI adapter only.

Case-specific behavior remains data-driven in `case.json` and `expected.json`.
V1 does not load arbitrary `grader.py` plugins from case directories; this keeps
the required benchmark auditable and prevents case code execution.

## Reference Fixtures

Each initial case includes:

- `good`: satisfies the full contract and should receive `strong`;
- `bad`: demonstrates the case's primary hard failure and must be blocked;
- `partial`: mathematically usable but missing a non-hard validation asset and
  should receive `needs_work` or `pass`, as specified by the case expectation.

Fixture expectations live in `benchmarks/fixtures/expectations.json`. The suite
test compares exact verdicts, hard-block IDs, and score ranges rather than one
fragile floating-point total.

## Outputs

One-case output:

```text
benchmark_result.json
benchmark_result.md
```

The JSON records case and submission hashes, rule results, dimension scores,
raw and capped totals, hard blocks, verdict, runtime budget result, and harness
version. The Markdown report presents the same data and an ordered remediation
list. It must not claim that `strong` predicts an award.

Suite output:

```text
benchmark_suite.json
benchmark_suite.md
```

The suite reports case/fixture coverage, verdict counts, dimension means, hard
block counts, and failed expectations. It returns non-zero if any expected
fixture result is violated or any case is invalid.

## Determinism And Security

- Use Python standard library only in the harness.
- Sort files, cases, rules, and report keys deterministically.
- Reject NaN and infinity.
- Resolve and constrain every path before reading.
- Do not execute submission commands in v1; grade recorded artifacts only.
- Verify committed input hashes before grading.
- Treat runtime as declared evidence backed by a valid run record, not as a
  separately trusted correctness signal.
- Do not access the network.

## Testing

Tests cover:

- valid and malformed case schemas;
- path traversal, absolute paths, and escaping symlinks;
- input and evidence hash mismatches;
- tolerance boundaries and non-finite metrics;
- dimension weighting and hard-block caps;
- all nine good/bad/partial fixture expectations;
- deterministic JSON/Markdown output across repeated runs;
- CLI exit codes and clean working-tree behavior;
- Python 3.11 and Python 3.13 compatibility.

Acceptance requires local `compileall`, the complete pytest suite, manifest
verification, and both GitHub checks. Benchmark CI must use no API keys and
consume no LLM tokens.

## Future Extensions

The v1 contracts intentionally support later additions without implementing
them now:

- licensed full historical competition cases;
- a live agent runner that exposes inputs and measures token/cost trajectories;
- AIDE-style candidate solution trees;
- optional Docker execution and replay;
- calibrated human or LLM review for writing quality and novelty.

These extensions must preserve the deterministic v1 suite as the required
regression baseline.
