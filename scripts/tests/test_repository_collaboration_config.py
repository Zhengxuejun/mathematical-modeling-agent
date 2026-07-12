from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]


def test_ci_workflow_has_required_triggers_permissions_and_commands() -> None:
    workflow = (ROOT / ".github/workflows/ci.yml").read_text(encoding="utf-8")
    for required in (
        "pull_request:",
        "push:",
        "workflow_dispatch:",
        "contents: read",
        "cancel-in-progress: true",
        'python-version: ["3.11", "3.13"]',
        "python -m compileall -q scripts",
        "python -m pytest -q",
    ):
        assert required in workflow


def test_public_collaboration_documents_exist() -> None:
    contributing = (ROOT / "CONTRIBUTING.md").read_text(encoding="utf-8")
    security = (ROOT / "SECURITY.md").read_text(encoding="utf-8")
    assert "pull request" in contributing.lower()
    assert "PACKAGE_MANIFEST.json" in contributing
    assert "private vulnerability reporting" in security.lower()
    assert "contest attachments" in security.lower()


def test_readme_links_collaboration_policies() -> None:
    readme = (ROOT / "README.md").read_text(encoding="utf-8")
    assert "[CONTRIBUTING.md](CONTRIBUTING.md)" in readme
    assert "[SECURITY.md](SECURITY.md)" in readme
    assert "Python 3.11" in readme
    assert "Python 3.13" in readme
