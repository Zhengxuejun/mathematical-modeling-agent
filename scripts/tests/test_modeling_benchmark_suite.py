from __future__ import annotations

import subprocess
import sys
from pathlib import Path

from scripts.benchmark.suite import run_suite, suite_json, suite_markdown, write_suite

ROOT = Path(__file__).resolve().parents[2]


def test_bundled_suite_meets_all_nine_expectations_and_is_deterministic(tmp_path: Path) -> None:
    fixtures = ROOT / "benchmarks/fixtures"
    first = run_suite(fixtures)
    second = run_suite(fixtures)
    assert first["fixture_count"] == 9
    assert first["passed_expectations"] == 9
    assert first["failed_expectations"] == []
    assert first["verdict_counts"] == {"blocked": 3, "needs_work": 3, "strong": 3}
    assert suite_json(first) == suite_json(second)
    assert suite_markdown(first) == suite_markdown(second)
    paths = write_suite(first, tmp_path)
    assert all(path.is_file() for path in paths)


def test_cli_validate_suite_and_single_run(tmp_path: Path) -> None:
    script = ROOT / "scripts/modeling_benchmark.py"
    validate = subprocess.run([sys.executable, str(script), "validate", "--cases", str(ROOT / "benchmarks/cases")], text=True, capture_output=True)
    assert validate.returncode == 0, validate.stdout + validate.stderr
    suite_output = tmp_path / "suite"
    suite = subprocess.run([sys.executable, str(script), "suite", "--fixtures", str(ROOT / "benchmarks/fixtures"), "--output", str(suite_output)], text=True, capture_output=True)
    assert suite.returncode == 0, suite.stdout + suite.stderr
    run_output = tmp_path / "run"
    run = subprocess.run([sys.executable, str(script), "run", "--case", str(ROOT / "benchmarks/cases/optimization_capacity"), "--submission", str(ROOT / "benchmarks/fixtures/optimization_capacity/good"), "--output", str(run_output)], text=True, capture_output=True)
    assert run.returncode == 0, run.stdout + run.stderr
    assert (suite_output / "benchmark_suite.json").is_file()
    assert (run_output / "benchmark_result.json").is_file()


def test_cli_missing_submission_does_not_create_it(tmp_path: Path) -> None:
    script = ROOT / "scripts/modeling_benchmark.py"
    missing = tmp_path / "missing"
    run = subprocess.run([sys.executable, str(script), "run", "--case", str(ROOT / "benchmarks/cases/optimization_capacity"), "--submission", str(missing)], text=True, capture_output=True)
    assert run.returncode == 2
    assert not missing.exists()
