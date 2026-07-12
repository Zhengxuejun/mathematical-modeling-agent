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


def test_public_copyright_holder_is_correct() -> None:
    license_text = (ROOT / "LICENSE").read_text(encoding="utf-8")
    notice = (ROOT / "NOTICE").read_text(encoding="utf-8")
    readme = (ROOT / "README.md").read_text(encoding="utf-8")
    incorrect_name = "郑学" + "军"
    for text in (license_text, notice, readme):
        assert "郑学君" in text
        assert incorrect_name not in text


def test_readme_links_collaboration_policies() -> None:
    readme = (ROOT / "README.md").read_text(encoding="utf-8")
    assert "[CONTRIBUTING.md](CONTRIBUTING.md)" in readme
    assert "[SECURITY.md](SECURITY.md)" in readme
    assert "Python 3.11" in readme
    assert "Python 3.13" in readme


def test_readme_exposes_end_to_end_competition_workflow() -> None:
    readme = (ROOT / "README.md").read_text(encoding="utf-8")
    workflow = (ROOT / "docs/competition-workflow.md").read_text(encoding="utf-8")
    assert "```mermaid" in readme
    assert "[docs/competition-workflow.md](docs/competition-workflow.md)" in readme
    for status in ("selected", "final_ready", "competition_ready", "S8 / completed"):
        assert status in readme
        assert status in workflow
    for step in (
        "data_audit",
        "model_skeleton",
        "candidate_solution_tree",
        "contest_evidence_sync",
        "contest_qc",
        "competition_readiness",
        "finalize",
    ):
        assert step in workflow
    assert "Pipeline 不会替团队自动完成这些模型脚本" in workflow
    ordered_steps = (
        "data_audit",
        "model_skeleton",
        "domain_checker_templates",
        "quality_gate",
        "quality_gate_plus",
        "problem_coverage",
        "result_interpretation",
        "report_assembly",
        "report_audit",
        "state_update_pre_finalize",
        "contest_evidence_sync",
        "contest_qc",
        "competition_evidence",
        "repair_advisor",
        "competition_readiness",
        "finalize",
        "state_update_final",
    )
    sequence = workflow.split("当前代码的实际执行顺序是：", 1)[1].split("```text", 1)[1].split("```", 1)[0]
    documented_steps = [line.removeprefix("→ ").strip() for line in sequence.splitlines() if line.strip()]
    assert documented_steps == list(ordered_steps)
