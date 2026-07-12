# Collaboration and CI Design

## Goal

Make contributions from friends and external GitHub users reviewable before they reach `main`. Every pull request and every push to `main` must run the repository's complete compile and test checks on supported Python versions.

This design does not automatically merge pull requests, deploy code, update the local checkout, or overwrite installed Codex/Hermes skill directories.

## Workflow

Add `.github/workflows/ci.yml` with these triggers:

- pull requests targeting `main`;
- pushes to `main`;
- manual `workflow_dispatch` runs.

The workflow uses read-only repository permissions and cancels an older run when a newer commit arrives for the same branch or pull request. It has a 10-minute timeout and tests Python 3.11 and Python 3.13 on `ubuntu-latest`.

Each matrix job performs:

1. checkout through `actions/checkout@v4`;
2. Python setup through `actions/setup-python@v5`;
3. `python -m compileall -q scripts`;
4. `python -m pytest -q`.

The expected check names are `Python 3.11` and `Python 3.13`. These names remain stable because branch protection refers to them directly.

## Contribution Contract

Add `CONTRIBUTING.md` with the supported path:

1. fork or create a feature branch;
2. keep changes scoped and preserve public CLI compatibility;
3. run compile and pytest locally;
4. update tests and `PACKAGE_MANIFEST.json` when repository files change;
5. open a pull request describing behavior, evidence, and compatibility impact;
6. merge only after required GitHub checks pass.

Contributors must not commit contest-private data, credentials, personal paths, generated caches, model weights, or upstream material whose license is not compatible with this repository.

Add `SECURITY.md` directing vulnerability and accidental-secret reports to GitHub private vulnerability reporting or a private maintainer channel. Public issues must not contain credentials, private contest attachments, or unpublished solutions.

## Main-Branch Protection

Branch protection is enabled only after the new workflow has completed successfully on GitHub. The `main` rule will:

- require pull requests for non-bypass contributors;
- require `Python 3.11` and `Python 3.13` checks;
- require the branch to be current before merging;
- block force pushes and branch deletion;
- leave administrator enforcement disabled so the repository owner can recover from CI or ruleset failures.

No approving-review count is required because a repository owner cannot approve their own pull request. The owner still reviews changes manually before merging.

## Documentation

Update `README.md` with the contribution flow and CI commands. Update `PACKAGE_MANIFEST.json` after all files are final so the published package inventory and hashes remain accurate.

## Verification

Completion requires all of the following evidence:

1. local compile succeeds;
2. all local pytest tests pass;
3. the CI workflow completes successfully for both Python versions on GitHub;
4. GitHub reports the exact required status checks in branch protection;
5. force pushes and branch deletion are disabled;
6. the local branch and `origin/main` point to the same commit;
7. the worktree is clean.

## Failure Handling

- If one Python version fails, branch protection is not enabled until the compatibility issue is fixed.
- If workflow permissions or action syntax fail, diagnose the GitHub run and push a corrective commit before applying branch protection.
- If branch protection prevents repository-owner recovery, use the administrator bypass; do not weaken required checks for ordinary contributors.
- If GitHub Actions is unavailable, keep the pull request unmerged and rely on local verification until the required checks recover.
