# Contest QC Evidence Sync Design

Date: 2026-07-12
Status: design ready for user review

## Goal

Reduce contest-time bookkeeping by discovering reproducible runs, result tables,
figures, and required deliverables from an existing modeling project and merging
them into Contest QC registries. Discovery must never promote an artifact to
`passed`, `paper_ready`, or equivalent trusted evidence without an explicit
validation action.

## Non-goals

- Do not infer that a mathematical model is correct from file existence.
- Do not replace project-specific domain checkers or human visual review.
- Do not rewrite confirmed registry rows or delete stale rows automatically.
- Do not parse arbitrary Python code to reconstruct hidden model semantics.
- Do not turn heuristic discovery into `competition_ready` evidence directly.

## User Workflow

The project scaffold adds `02_代码/18_contest_evidence_sync.py`. During a
competition, the team runs it after producing or updating model outputs:

```bash
python 02_代码/18_contest_evidence_sync.py --dry-run
python 02_代码/18_contest_evidence_sync.py
```

The dry run writes no registry changes and prints a deterministic summary. The
normal run initializes missing Contest QC registries, discovers candidate
evidence, merges only safe fields, and writes a machine-readable sync report.
The team then reviews candidate rows, adds model semantics and validation
results, and runs the existing `contest_qc_gate.py` phases.

## Inputs And Outputs

The synchronizer reads only project-local files:

- `06_过程记录/problem_analysis.md` for question and deliverable candidates;
- `02_代码/` for runnable Python entry points;
- `03_结果表格/` for CSV/XLSX result candidates;
- `04_图表/` for PNG/JPG/JPEG/PDF/SVG figure candidates;
- `06_过程记录/竞赛质控/run_record.csv` for confirmed run linkage;
- existing Contest QC registries for non-destructive merging.

It updates these registries when safe:

- `deliverable_matrix.csv`;
- `result_registry.csv`;
- `figure_evidence.csv`.

It does not synthesize `math_verification.csv`, `claim_ledger.csv`, review
findings, compliance declarations, or completed run records because those
require semantic or execution evidence.

Every non-dry-run execution writes:

- `06_过程记录/竞赛质控/evidence_sync.json`;
- `06_过程记录/竞赛质控/evidence_sync.md`.

The report records discovered, added, unchanged, conflicted, and ignored items,
plus the reason for every ignored or conflicted item.

## Discovery Rules

### Deliverables

Questions are extracted using the established problem-coverage parser rather
than a second regular-expression implementation. Each extracted question gets
a stable candidate `deliverable_id` derived from its normalized question ID.
New rows use `status=candidate` and leave ownership and evidence requirements
for review where they cannot be inferred reliably.

### Result Tables

CSV and XLSX files under `03_结果表格/` become result candidates. Generated
audit, registry, manifest, and pipeline-control files are excluded. A table is
linked to an existing completed run only when the normalized project-relative
path appears in that run's `output_tables`; otherwise `run_id` remains empty.
New rows use `validation_status=candidate` and do not invent metric values,
units, scenarios, or baselines.

### Figures

Supported figure files under `04_图表/` become figure candidates. A figure is
linked to a completed run only through an exact normalized path match in
`output_figures`. New rows use `validation_status=candidate`; caption,
post-figure conclusion, render status, and human visual status remain empty.

### Stable Identity

Identity is based on normalized project-relative paths for files and normalized
question IDs for deliverables. Recognized question IDs remain readable, such as
`D-Q1`; file-backed IDs and fallback question IDs use a short deterministic
SHA-256 suffix so repeated runs and Python versions produce identical rows.

## Merge And Safety Policy

The synchronizer acquires an advisory lock in the QC directory before writing.
It reads and validates the current CSV header before any mutation. A malformed
registry produces a blocking error and no registry is changed.

Merge behavior is field-aware:

- existing non-empty values always win;
- existing trusted states such as `provided` and `paper_ready` are preserved;
- empty safe fields may be filled from exact project-local evidence;
- new rows are always candidates;
- missing files create report warnings but do not delete registry rows;
- ambiguous question or run linkage is reported as a conflict and left blank.

All changed registries are prepared in memory, written to temporary sibling
files, flushed, and validated before replacement. Before replacing any target,
the synchronizer records a transaction journal and same-directory backups. A
handled replacement failure rolls back every changed target; an interrupted
process is detected and recovered from the journal on the next invocation.
The journal is removed only after all registry replacements and report writes
complete. This gives the registry set recoverable transaction semantics even
though a filesystem cannot atomically replace several files at once.

## Architecture

Add `scripts/contest_evidence_sync.py` with small, testable units:

- project inventory and path normalization;
- question extraction adapter;
- completed-run index;
- candidate builders for the three registries;
- schema-aware merge engine;
- journaled multi-file writer and recovery routine;
- Markdown/JSON report renderer;
- CLI entry point.

`create_modeling_project.py` creates the project wrapper. The full modeling
pipeline runs evidence sync immediately before the final Contest QC gate, after
report assembly and report audit have produced the latest artifacts. Sync
conflicts or schema errors block that step; ordinary candidate/review warnings
remain visible but do not masquerade as QC failures.

The synchronizer may reuse public parsing helpers from existing modules. Shared
logic will be extracted only where required to avoid circular imports or CLI
side effects.

## Error Handling

- Missing project or malformed CSV schema: exit 2 without mutation.
- Unsafe path, project-external symlink, or unsupported file: ignore and report.
- Ambiguous linkage or missing completed run: create an unlinked candidate and
  report a warning.
- Duplicate identity with contradictory trusted values: preserve the existing
  row, report a conflict, and exit 1 after producing the sync report.
- Successful sync with review-only candidates: exit 0.

## Pipeline And Readiness Boundary

The pipeline summary exposes sync counts and status. `contest_qc_gate.py`
continues to be the authority for `early_ready`, `model_ready`, and
`final_ready`. `competition_readiness_gate.py` does not consume candidates as
proof. Consequently, automatic sync reduces manual entry but cannot bypass
formal runs, mathematical checks, claim linkage, figure review, or compliance
checks.

## Testing

Tests cover:

- empty and partially initialized projects;
- deterministic IDs and ordering on Python 3.11 and 3.13;
- repeated idempotent sync;
- preservation of manually confirmed rows and trusted states;
- exact completed-run linkage and ambiguous/unlinked cases;
- exclusion of control/audit files and project-external symlinks;
- malformed headers and all-or-nothing writes;
- dry-run behavior;
- scaffold wrapper generation;
- pipeline ordering before Contest QC;
- an end-to-end fixture where candidates remain insufficient for final readiness
  until explicitly validated.

Acceptance requires `compileall` and the complete pytest suite to pass locally,
followed by the repository's Python 3.11 and Python 3.13 GitHub checks after the
implementation is pushed.

## Documentation And Release Surface

Update `README.md`, `SKILL.md`, `references/contest-quality-gate.md`,
`references/continuous-optimization-notes.md`, `RELEASE_NOTES.md`, and
`PACKAGE_MANIFEST.json`. Documentation must consistently call synchronized rows
"candidates" and state that file discovery is not validation.
