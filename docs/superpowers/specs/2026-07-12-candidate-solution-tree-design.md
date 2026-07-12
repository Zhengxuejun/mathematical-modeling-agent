# Candidate Solution Tree Design

Date: 2026-07-12
Status: implementation ready

## Goal

Add an AIDE-style, bounded candidate solution tree that lets a competition team
record alternative models, preserve parent-child improvement hypotheses,
evaluate real run artifacts, and select the strongest eligible candidate with a
deterministic explanation.

The component is an independent implementation of the candidate-search pattern.
It does not copy AIDE source code, prompts, datasets, or execution machinery.

## Scope

V1 manages experiments that have already been produced by a human or agent. It:

- registers project-local candidate submissions;
- records parent-child lineage and the hypothesis behind each branch;
- validates claimed runs, feasibility, validation, metrics, and evidence hashes;
- optionally evaluates every candidate against one Modeling Benchmark case;
- selects a candidate only from nodes that pass all required gates;
- writes machine-readable and human-readable tree reports.

V1 does not generate model code, call an LLM, execute a submission command,
search indefinitely, or publish the selected candidate as a final contest
answer.

## User Workflow

Initialize a bounded tree:

```bash
python scripts/candidate_solution_tree.py init PROJECT \
  --objective-metric objective \
  --direction maximize \
  --validation-metric validation_score
```

Register a baseline and a child improvement:

```bash
python scripts/candidate_solution_tree.py add PROJECT \
  --submission 08_候选方案/baseline \
  --label baseline \
  --hypothesis "establish a reproducible lower bound"

python scripts/candidate_solution_tree.py add PROJECT \
  --submission 08_候选方案/robust_model \
  --parent C001 \
  --label robust-model \
  --hypothesis "group-aware validation reduces optimistic error"
```

Evaluate and select:

```bash
python scripts/candidate_solution_tree.py evaluate PROJECT --candidate C001
python scripts/candidate_solution_tree.py evaluate PROJECT --candidate C002 \
  --benchmark-case benchmarks/cases/prediction_group_leakage
python scripts/candidate_solution_tree.py select PROJECT
python scripts/candidate_solution_tree.py status PROJECT
```

## Storage Contract

Tree state and reports live under:

```text
06_过程记录/候选方案树/
  candidate_tree.json
  candidate_tree.md
  candidate_tree.lock
```

The JSON schema contains:

- schema and tool version;
- objective metric and `maximize`/`minimize` direction;
- validation metric constrained to `[0, 1]`;
- maximum candidate count and maximum depth;
- selected candidate ID or null;
- ordered candidate nodes.

Every node records:

- stable sequential ID (`C001`, `C002`, ...);
- optional parent ID;
- project-local submission path;
- short label and explicit improvement hypothesis;
- `registered`, `evaluated`, `blocked`, or `selected` status;
- immutable evaluation snapshot after each evaluation.

The tree rejects duplicate submission paths, unknown parents, cycles, depth or
candidate-limit overflow, unsafe paths, escaping symlinks, malformed state, and
non-finite metrics.

## Candidate Submission Contract

Each candidate directory contains:

```text
solution.json
run_record.json
report.md
artifacts/
```

`solution.json` must include:

- non-empty `model_name` and `model_version`;
- integer `random_seed`;
- finite numeric objective and validation metrics;
- `checks.feasible=true`;
- `checks.validation_passed=true`;
- at least one evidence path.

`run_record.json` must include:

- non-empty command recorded for replay, but never executed by this tool;
- finite non-negative runtime;
- `exit_code=0`;
- artifact paths mapped to SHA-256 values.

Every evidence path must resolve inside the candidate directory, exist, and
match the run record hash. Missing or mismatched evidence blocks the node.

## Evaluation And Selection

Evaluation produces explicit gates:

```text
contract_valid
run_succeeded
feasible
validation_passed
evidence_verified
benchmark_eligible (when a benchmark case is supplied)
```

A node is eligible only when every applicable gate passes. Failed nodes remain
in the tree as `blocked`; they are evidence about unsuccessful branches, not
deleted attempts.

Selection is deterministic and lexicographic:

1. only eligible evaluated nodes;
2. benchmark total descending when all eligible nodes have the same case hash;
3. validation score descending;
4. configured objective direction;
5. verified evidence count descending;
6. runtime ascending;
7. candidate ID ascending.

If any eligible node has Benchmark evidence, every eligible node must have the
same Benchmark case hash. Mixed or incomparable Benchmark coverage blocks
selection instead of silently favoring a measured candidate.

Selecting a new node returns the previous selection to `evaluated`. The report
states the ordered comparison values and why blocked nodes were excluded.

## Trust Boundaries

- The tool reads artifacts and never executes candidate commands.
- All candidate paths must remain inside the modeling project.
- A Benchmark `needs_work`, `blocked`, or `invalid` result is not selection
  eligible when Benchmark evaluation is requested.
- `selected` means best eligible node under the configured local comparison. It
  does not mean mathematically proven, `paper_ready`, `final_ready`, or
  `competition_ready`.
- The component never edits Contest QC, competition evidence, readiness, final
  package, or S0-S8 status files.
- Tree writes use a lock and atomic replacement to avoid partial state.

## Scaffold Integration

New projects receive:

```text
02_代码/19_candidate_solution_tree.py
08_候选方案/README.md
```

The wrapper exposes the repository implementation. The Pipeline does not run
the tree automatically because experiment creation and selection are deliberate
modeling decisions, not a mandatory packaging step.

## Testing And Acceptance

Tests cover initialization, bounded IDs/depth, safe paths and symlinks,
lineage, blocked run/feasibility/validation/evidence cases, Benchmark
integration, incomparable Benchmark protection, deterministic selection,
reselection, report output, CLI behavior, scaffold portability, and readiness
isolation.

Acceptance requires compileall, the complete pytest suite, manifest verification,
and real GitHub checks on Python 3.11 and Python 3.13.

