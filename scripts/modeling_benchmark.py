#!/usr/bin/env python3
from __future__ import annotations

import argparse
from pathlib import Path

from benchmark.contracts import ContractError, load_case
from benchmark.grader import grade
from benchmark.reporting import write_result


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Deterministic offline mathematical-modeling benchmark")
    commands = parser.add_subparsers(dest="command", required=True)
    run = commands.add_parser("run", help="grade one submission")
    run.add_argument("--case", type=Path, required=True)
    run.add_argument("--submission", type=Path, required=True)
    run.add_argument("--output", type=Path)
    validate = commands.add_parser("validate", help="validate case definitions")
    validate.add_argument("--cases", type=Path, required=True)
    suite = commands.add_parser("suite", help="run bundled reference fixtures")
    suite.add_argument("--fixtures", type=Path, required=True)
    suite.add_argument("--output", type=Path, default=Path("benchmark-results"))
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    if args.command == "run":
        result = grade(args.case, args.submission)
        output = args.output or args.submission / "06_过程记录" / "benchmark"
        write_result(result, output)
        print(f"{result.case_id}: {result.verdict} ({result.total_score:.2f})")
        return 0 if result.verdict not in {"invalid", "blocked"} else 1
    if args.command == "validate":
        failures = []
        for case_dir in sorted(path for path in args.cases.iterdir() if path.is_dir()):
            try:
                load_case(case_dir)
                print(f"valid: {case_dir.name}")
            except (ContractError, OSError) as exc:
                failures.append(f"{case_dir.name}: {exc}")
        for failure in failures:
            print(f"invalid: {failure}")
        return 1 if failures else 0
    from benchmark.suite import run_suite, write_suite
    result = run_suite(args.fixtures)
    write_suite(result, args.output)
    print(f"fixtures: {result['passed_expectations']}/{result['fixture_count']} expectations passed")
    return 0 if not result["failed_expectations"] else 1


if __name__ == "__main__":
    raise SystemExit(main())

