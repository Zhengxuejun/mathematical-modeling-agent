# Candidate Solution Tree Implementation Plan

**Goal:** Add a bounded AIDE-style experiment tree that evaluates project-local candidate submissions from recorded artifacts and selects the strongest eligible branch without executing code or affecting contest readiness.

**Architecture:** A focused standard-library package owns state contracts, safe paths, evaluation, deterministic ranking, locking, atomic reports, and a thin CLI. It reuses the existing Modeling Benchmark grader only when a caller supplies a compatible case.

## Task 1: State Contract And Bounded Lineage

- [ ] Write failing tests for initialization, stable IDs, parent lookup, duplicate submissions, candidate limits, depth limits, traversal, and escaping symlinks.
- [ ] Implement `scripts/candidate_tree/contracts.py`, `paths.py`, and `store.py`.
- [ ] Use schema validation, a lock, and atomic replacement for every mutation.
- [ ] Verify the focused contract tests and commit.

## Task 2: Artifact Evaluation And Hard Gates

- [ ] Write failing tests for successful candidates, non-zero runs, infeasibility, failed validation, non-finite metrics, missing evidence, and hash mismatch.
- [ ] Implement read-only candidate evaluation in `scripts/candidate_tree/evaluation.py`.
- [ ] Snapshot objective, validation, runtime, evidence hashes, gates, and blocking reasons.
- [ ] Prove evaluation never invokes the recorded command and never touches readiness files.
- [ ] Verify focused evaluation tests and commit.

## Task 3: Benchmark Integration And Deterministic Selection

- [ ] Write failing tests for Benchmark pass/strong eligibility and needs_work/blocked rejection.
- [ ] Reject selection when eligible nodes have mixed or different Benchmark case hashes.
- [ ] Implement the documented lexicographic ranking and reselection semantics in `selection.py`.
- [ ] Emit exact comparison evidence for every ranked node.
- [ ] Verify selection tests and commit.

## Task 4: Reports, CLI, And Scaffold

- [ ] Implement deterministic JSON state and readable Markdown reports.
- [ ] Add `init`, `add`, `evaluate`, `select`, and `status` CLI commands.
- [ ] Add project wrapper `02_代码/19_candidate_solution_tree.py` and `08_候选方案/README.md`.
- [ ] Extend scaffold portability tests and run a temporary-project CLI workflow.
- [ ] Commit the integration increment.

## Task 5: Documentation, Manifest, And Review

- [ ] Update README, SKILL, release notes, and continuous optimization notes.
- [ ] Regenerate and verify `PACKAGE_MANIFEST.json`.
- [ ] Run compileall, focused tests, full pytest, CLI smoke, and diff checks.
- [ ] Review function contracts, state transitions, cleanup, module boundaries, security, and readiness isolation.

## Task 6: GitHub Delivery

- [ ] Push `codex/candidate-solution-tree` and open a focused pull request.
- [ ] Confirm Python 3.11 and Python 3.13 GitHub checks pass.
- [ ] Squash-merge, synchronize local main, remove the temporary worktree and branch, and verify local/remote parity.

