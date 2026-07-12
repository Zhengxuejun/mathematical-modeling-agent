# Modeling Benchmark Harness Implementation Plan

**Goal:** Add a deterministic offline benchmark that grades explicit mathematical-modeling artifacts across optimization, prediction, and evaluation failure modes without network access, API keys, LLM calls, or effects on competition readiness.

**Architecture:** A standard-library package under `scripts/benchmark/` validates data-only case and submission contracts, applies reusable declarative rules, calculates dimension scores and hard-block caps, and emits deterministic JSON/Markdown. A thin CLI runs one case, validates all cases, or checks the bundled fixture suite.

**Tech Stack:** Python 3.11/3.13 standard library, JSON/CSV/Markdown, pytest, existing repository CI and package manifest.

## File Map

- Create `scripts/benchmark/{__init__,contracts,paths,rules,grader,reporting,suite}.py`.
- Create `scripts/modeling_benchmark.py`.
- Create `scripts/tests/test_modeling_benchmark_{contracts,rules,grader,suite,cli}.py`.
- Create three directories under `benchmarks/cases/` and nine submissions under `benchmarks/fixtures/`.
- Modify `README.md`, `SKILL.md`, `RELEASE_NOTES.md`, and `references/continuous-optimization-notes.md`.
- Regenerate `PACKAGE_MANIFEST.json` after all release files are final.

## Task 1: Contracts And Safe Paths

- [ ] Write failing tests for valid case loading, unknown dimensions, invalid weights, duplicate rule IDs, unsafe relative paths, escaping symlinks, input hash mismatch, missing submission files, and non-finite numeric values.
- [ ] Implement typed dataclasses and strict JSON loaders in `contracts.py`.
- [ ] Implement local-path resolution, file inventory, and SHA-256 helpers in `paths.py`.
- [ ] Verify with `python3 -m pytest -q scripts/tests/test_modeling_benchmark_contracts.py`.
- [ ] Commit the contract increment.

Acceptance: malformed or untrusted contracts produce deterministic validation errors and no path can resolve outside its declared root.

## Task 2: Declarative Rules, Scoring, And Verdicts

- [ ] Write failing boundary tests for exact, tolerance, boolean, range, ranking, evidence, input-hash, run-record, and runtime-budget rules.
- [ ] Add tests for weighted dimension means, 0-100 totals, core-dimension thresholds, integrity invalidation, and mathematical/statistical hard-block caps.
- [ ] Implement reusable data-driven rule evaluation in `rules.py` with no dynamic imports or executable expressions.
- [ ] Implement orchestration and verdict calculation in `grader.py`.
- [ ] Verify with `python3 -m pytest -q scripts/tests/test_modeling_benchmark_rules.py scripts/tests/test_modeling_benchmark_grader.py`.
- [ ] Commit the grading increment.

Acceptance: every rule returns a normalized score and evidence; integrity failures score zero, invalid mathematics cannot pass, and benchmark results do not read or modify competition-readiness artifacts.

## Task 3: Reports And CLI

- [ ] Write failing tests for stable JSON key order/content, stable Markdown, default output paths, custom output directories, and command exit codes.
- [ ] Implement `reporting.py` with byte-stable output that excludes wall-clock timestamps.
- [ ] Implement `modeling_benchmark.py` subcommands `run`, `validate`, and `suite` using `argparse`.
- [ ] Ensure `run` writes only under the submission benchmark directory unless `--output` is supplied.
- [ ] Verify CLI behavior in temporary directories and confirm the repository remains clean.
- [ ] Commit the reporting and CLI increment.

Acceptance: repeated runs over identical inputs produce identical report bytes; invalid contracts and failed suite expectations return non-zero.

## Task 4: Three Cases And Nine Reference Fixtures

- [ ] Add the `optimization_capacity` case and good/bad/partial submissions; prove infeasibility blocks a superficially good objective.
- [ ] Add the `prediction_group_leakage` case and good/bad/partial submissions; prove explicit leakage blocks a low-error result.
- [ ] Add the `evaluation_rank_stability` case and good/bad/partial submissions; prove missing stability analysis loses credit without fabricating a hard failure.
- [ ] Add `benchmarks/fixtures/expectations.json` with exact verdicts, hard-block IDs, and score ranges.
- [ ] Implement deterministic fixture discovery and aggregation in `suite.py`.
- [ ] Verify all nine expectations and exact repeated suite output.
- [ ] Commit the benchmark corpus and suite increment.

Acceptance: good fixtures are `strong`, primary bad fixtures are `blocked` or `invalid` as specified, partial fixtures remain diagnostically useful, and all cases are original synthetic microcases.

## Task 5: Documentation, Manifest, And Full Verification

- [ ] Document purpose, commands, score limits, offline behavior, and the non-integration boundary with `competition_ready`.
- [ ] Add the harness to skill and continuous-optimization references without claiming award prediction.
- [ ] Add release notes and regenerate `PACKAGE_MANIFEST.json` with sorted paths, byte counts, hashes, and updated file count.
- [ ] Run `python3 -m compileall -q scripts`.
- [ ] Run `python3 -m pytest -q`.
- [ ] Run case validation and the bundled suite from a temporary output directory.
- [ ] Verify every manifest entry and confirm no absolute home path, cache, generated report, or unlicensed contest material is committed.
- [ ] Review the complete diff for behavioral regressions, unsafe assumptions, and unrelated edits.

Acceptance: the full local suite passes, manifest contents match the repository, and the worktree contains only intended source, tests, synthetic fixtures, and documentation.

## Task 6: GitHub Delivery

- [ ] Push `codex/modeling-benchmark-harness` and open a focused pull request.
- [ ] Confirm the real GitHub Actions jobs for Python 3.11 and Python 3.13 both pass.
- [ ] Address any review or CI findings, then squash-merge the pull request.
- [ ] Fast-forward local `main`, remove the temporary worktree/branch where safe, and verify local/remote hash parity plus a clean worktree.

Acceptance: the merged commit is on public `origin/main`, both required GitHub checks passed, and local `main` matches the remote.
