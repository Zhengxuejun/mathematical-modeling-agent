# Contest Evidence Sync Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add a non-destructive synchronizer that discovers project deliverables, result tables, and figures as review-only Contest QC candidates without upgrading them to trusted evidence.

**Architecture:** A new standard-library CLI reads the established Contest QC schemas, reuses the existing question extractor, builds deterministic candidates, and merges them by stable identity. Registry writes use validation, a lock, backups, a transaction journal, rollback, and startup recovery; the scaffold and full pipeline call the synchronizer before the final QC gate.

**Tech Stack:** Python 3.11/3.13 standard library, CSV/JSON/Markdown, pytest, existing Contest QC and pipeline modules.

---

## File Map

- Create `scripts/contest_evidence_sync.py`: inventory, discovery, merge, transaction recovery, report, and CLI.
- Create `scripts/tests/test_contest_evidence_sync.py`: focused discovery, merge, safety, dry-run, and readiness-boundary tests.
- Modify `scripts/create_modeling_project.py`: generate wrapper `02_代码/18_contest_evidence_sync.py` and document the command.
- Modify `scripts/tests/test_create_modeling_project_portability.py`: verify wrapper portability and initialized output location.
- Modify `scripts/modeling_pipeline.py`: run evidence sync before Contest QC and expose summary counts.
- Modify `scripts/tests/test_modeling_pipeline_order.py`: lock pipeline ordering.
- Modify `scripts/tests/test_competition_grade_e2e.py`: prove candidates do not downgrade confirmed evidence or bypass readiness.
- Modify `README.md`, `SKILL.md`, `references/contest-quality-gate.md`, `references/continuous-optimization-notes.md`, `RELEASE_NOTES.md`: document usage and trust boundary.
- Modify `PACKAGE_MANIFEST.json`: include changed release files with current hashes and counts.

### Task 1: Candidate Discovery And Stable Identity

**Files:**
- Create: `scripts/tests/test_contest_evidence_sync.py`
- Create: `scripts/contest_evidence_sync.py`

- [ ] **Step 1: Write failing discovery tests**

Create fixtures with `problem_analysis.md`, one completed run, two result tables,
one figure, one control table, and an external symlink. Assert that:

```python
summary = build_sync(project)
assert [row["deliverable_id"] for row in summary.registries["deliverable_matrix.csv"].candidates] == ["D-Q1"]
assert {row["source_table"] for row in summary.registries["result_registry.csv"].candidates} == {
    "03_结果表格/model_results.csv",
    "03_结果表格/sensitivity_results.xlsx",
}
linked = next(row for row in summary.registries["result_registry.csv"].candidates if row["source_table"].endswith("model_results.csv"))
assert linked["run_id"] == "R1"
assert linked["source_script"] == "02_代码/solve.py"
assert linked["validation_status"] == "candidate"
assert summary.counts["ignored"] == 2
```

- [ ] **Step 2: Run the test and verify failure**

Run: `python3 -m pytest -q scripts/tests/test_contest_evidence_sync.py`

Expected: collection fails because `contest_evidence_sync` does not exist.

- [ ] **Step 3: Implement inventory and deterministic builders**

Define these public types and functions:

```python
@dataclass
class RegistrySync:
    name: str
    candidates: list[dict[str, str]]
    merged_rows: list[dict[str, str]]
    added: int = 0
    updated: int = 0
    unchanged: int = 0
    conflicts: list[str] = field(default_factory=list)

@dataclass
class SyncSummary:
    project: Path
    registries: dict[str, RegistrySync]
    counts: dict[str, int]
    warnings: list[str]
    ignored: list[dict[str, str]]

def stable_id(prefix: str, identity: str) -> str:
    digest = hashlib.sha256(identity.encode("utf-8")).hexdigest()[:10].upper()
    return f"{prefix}-{digest}"

def safe_relative_file(project: Path, path: Path) -> str | None:
    try:
        resolved = path.resolve(strict=True)
        return resolved.relative_to(project.resolve()).as_posix()
    except (FileNotFoundError, ValueError):
        return None
```

Use `problem_coverage_tracker.extract_questions()` for question discovery. Use
exact normalized paths from completed `run_record.csv` rows to link tables and
figures. Exclude audit/control names through an explicit lowercase basename set.
Sort candidates by their identity path or normalized question ID before IDs and
rows are produced. Implement `build_sync(project: Path) -> SyncSummary` by
loading the three target registries with `REGISTRY_HEADERS`, indexing completed
runs by every normalized `output_tables` and `output_figures` path, creating
candidate dictionaries with all schema fields present, and returning aggregate
counts from the three `RegistrySync` objects.

- [ ] **Step 4: Run focused tests**

Run: `python3 -m pytest -q scripts/tests/test_contest_evidence_sync.py -k 'discover or stable or link'`

Expected: all selected tests pass.

- [ ] **Step 5: Commit the discovery increment**

```bash
git add scripts/contest_evidence_sync.py scripts/tests/test_contest_evidence_sync.py
git commit -m "feat: discover contest evidence candidates"
```

### Task 2: Conservative Merge, Dry Run, And Transaction Recovery

**Files:**
- Modify: `scripts/tests/test_contest_evidence_sync.py`
- Modify: `scripts/contest_evidence_sync.py`

- [ ] **Step 1: Add failing merge and recovery tests**

Add tests proving that a second sync is idempotent, `provided` and
`paper_ready` survive unchanged, malformed headers mutate nothing, dry-run
writes no registry or report, contradictory duplicate identities return a
conflict, an interrupted journal restores backups, and an injected replacement
failure rolls back all three registries.

```python
first = synchronize(project)
second = synchronize(project)
assert first.counts["added"] == 3
assert second.counts["added"] == 0
assert second.counts["unchanged"] == 3
assert load_rows(qc / "deliverable_matrix.csv")[0]["status"] == "provided"
assert load_rows(qc / "result_registry.csv")[0]["validation_status"] == "paper_ready"
```

- [ ] **Step 2: Run tests and verify the new failures**

Run: `python3 -m pytest -q scripts/tests/test_contest_evidence_sync.py -k 'merge or dry_run or recovery or malformed'`

Expected: failures identify missing merge, transaction, and CLI behavior.

- [ ] **Step 3: Implement schema-aware merge and recoverable writes**

Add these module boundaries with the exact signatures shown:

```text
IDENTITY_FIELDS = {
    "deliverable_matrix.csv": "deliverable_id",
    "result_registry.csv": "source_table",
    "figure_evidence.csv": "figure_path",
}
validate_header(path: Path, expected: list[str]) -> None
merge_registry(name: str, existing: list[dict[str, str]], candidates: list[dict[str, str]]) -> RegistrySync
recover_transaction(qc_dir: Path) -> None
write_transaction(project: Path, registries: dict[str, RegistrySync], reports: dict[str, str]) -> None
synchronize(project: Path, dry_run: bool = False) -> SyncSummary
```

Use `fcntl.flock` on the QC lock file for supported Unix runners. The journal
contains target, backup, and temporary paths plus phase. Flush and `os.fsync`
temporary files and the journal. On a handled error, restore backups in reverse
order. At startup, recover any non-committed journal before reading registries.
Never overwrite a non-empty existing field; report differing non-empty values
as conflicts while preserving the existing row.

- [ ] **Step 4: Implement reports and CLI exit codes**

Add `write_reports()` and `main()` supporting:

```text
python scripts/contest_evidence_sync.py PROJECT [--dry-run]
```

Exit `2` for missing project or schema failure, `1` for merge conflicts, and `0`
for successful candidate sync. JSON contains version, generated time, project,
counts, warnings, ignored items, and per-registry changes. Markdown presents the
same facts without claiming validation.

- [ ] **Step 5: Run all synchronizer tests and commit**

Run: `python3 -m pytest -q scripts/tests/test_contest_evidence_sync.py`

Expected: all tests pass.

```bash
git add scripts/contest_evidence_sync.py scripts/tests/test_contest_evidence_sync.py
git commit -m "feat: safely merge contest evidence registries"
```

### Task 3: Project Scaffold Integration

**Files:**
- Modify: `scripts/create_modeling_project.py`
- Modify: `scripts/tests/test_create_modeling_project_portability.py`

- [ ] **Step 1: Add a failing scaffold assertion**

```python
wrapper = project / "02_代码" / "18_contest_evidence_sync.py"
assert wrapper.is_file()
text = wrapper.read_text(encoding="utf-8")
assert str(SCRIPT_DIR / "contest_evidence_sync.py") in text
assert "__SKILL_SCRIPT_DIR__" not in text
```

- [ ] **Step 2: Run the scaffold test and verify failure**

Run: `python3 -m pytest -q scripts/tests/test_create_modeling_project_portability.py`

Expected: failure because wrapper 18 is absent.

- [ ] **Step 3: Add the wrapper and project README command**

Add this `SCRIPT_TEMPLATES` entry and insert its command before final Contest QC:

```python
"18_contest_evidence_sync.py": """from pathlib import Path
import subprocess
import sys

BASE = Path(__file__).resolve().parents[1]
SCRIPT = Path('__SKILL_SCRIPT_DIR__/contest_evidence_sync.py')
raise SystemExit(subprocess.call([sys.executable, str(SCRIPT), str(BASE)] + sys.argv[1:]))
""",
```

- [ ] **Step 4: Run the scaffold tests and commit**

Run: `python3 -m pytest -q scripts/tests/test_create_modeling_project_portability.py scripts/tests/test_contest_qc_gate.py`

Expected: all tests pass.

```bash
git add scripts/create_modeling_project.py scripts/tests/test_create_modeling_project_portability.py
git commit -m "feat: scaffold contest evidence sync wrapper"
```

### Task 4: Pipeline Integration And Readiness Boundary

**Files:**
- Modify: `scripts/modeling_pipeline.py`
- Modify: `scripts/tests/test_modeling_pipeline_order.py`
- Modify: `scripts/tests/test_competition_grade_e2e.py`

- [ ] **Step 1: Add failing pipeline-order and boundary tests**

Require:

```python
assert names.index("report_audit") < names.index("contest_evidence_sync")
assert names.index("contest_evidence_sync") < names.index("contest_qc")
```

Extend the end-to-end fixture with an unregistered extra table and figure. After
the pipeline, assert they appear as `candidate`, the existing `paper_ready` rows
remain trusted, `contest_qc_readiness == "final_ready"`, and candidate rows alone
cannot make an otherwise incomplete fixture final-ready.

- [ ] **Step 2: Run tests and verify failure**

Run: `python3 -m pytest -q scripts/tests/test_modeling_pipeline_order.py scripts/tests/test_competition_grade_e2e.py`

Expected: ordering failure because the new step is absent.

- [ ] **Step 3: Add the pipeline command and summary fields**

Define `CONTEST_EVIDENCE_SYNC_SCRIPT`, add `--skip-contest-evidence-sync`, and
run the command after report audit and before Contest QC. Read
`evidence_sync.json` and expose:

```python
"evidence_sync_counts": evidence_sync_summary.get("counts", {}),
"evidence_sync_status": evidence_sync_summary.get("status"),
```

Candidate/review warnings do not fail the command. Schema, transaction, or
merge-conflict exit codes fail the pipeline and prevent final QC/package steps.

- [ ] **Step 4: Run pipeline tests and commit**

Run: `python3 -m pytest -q scripts/tests/test_modeling_pipeline_order.py scripts/tests/test_competition_grade_e2e.py`

Expected: all tests pass.

```bash
git add scripts/modeling_pipeline.py scripts/tests/test_modeling_pipeline_order.py scripts/tests/test_competition_grade_e2e.py
git commit -m "feat: synchronize evidence before contest QC"
```

### Task 5: Documentation, Package Metadata, And Full Verification

**Files:**
- Modify: `README.md`
- Modify: `SKILL.md`
- Modify: `references/contest-quality-gate.md`
- Modify: `references/continuous-optimization-notes.md`
- Modify: `RELEASE_NOTES.md`
- Modify: `PACKAGE_MANIFEST.json`

- [ ] **Step 1: Document the operating sequence and trust boundary**

Add the dry-run and normal commands, list the three synchronized registries,
and state consistently: synchronized rows are candidates; file discovery does
not prove model correctness, result validity, visual quality, or readiness.
Record the new component as implemented in continuous optimization notes.

- [ ] **Step 2: Refresh the package manifest**

Recompute every tracked release file's byte count and SHA-256 in sorted path
order, update `file_count`, and keep `.git`, `.pytest_cache`, `__pycache__`, and
`.DS_Store` excluded. Include the new design, plan, script, test, and updated
documentation files.

- [ ] **Step 3: Run static and complete test verification**

Run:

```bash
python3 -m compileall -q scripts
python3 -m pytest -q
git diff --check
git status --short
```

Expected: compile succeeds, the complete test suite passes, diff check is empty,
and status contains only intended files.

- [ ] **Step 4: Commit release-surface updates**

```bash
git add README.md SKILL.md RELEASE_NOTES.md PACKAGE_MANIFEST.json references/contest-quality-gate.md references/continuous-optimization-notes.md
git commit -m "docs: document contest evidence synchronization"
```

- [ ] **Step 5: Verify both supported Python versions through GitHub**

Push the completed branch, inspect the resulting GitHub Actions run, and require
both `test (3.11)` and `test (3.13)` to conclude successfully before declaring
the enhancement complete.
