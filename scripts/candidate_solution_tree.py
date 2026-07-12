#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from scripts.candidate_tree.contracts import TreeError
from scripts.candidate_tree.service import add_candidate, evaluate_candidate, get_tree, initialize_tree, select_candidate


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Bounded candidate solution tree for mathematical modeling")
    commands = parser.add_subparsers(dest="command", required=True)
    init = commands.add_parser("init", help="initialize a candidate tree")
    init.add_argument("project", type=Path)
    init.add_argument("--objective-metric", required=True)
    init.add_argument("--direction", choices=("maximize", "minimize"), required=True)
    init.add_argument("--validation-metric", default="validation_score")
    init.add_argument("--max-candidates", type=int, default=12)
    init.add_argument("--max-depth", type=int, default=3)
    add = commands.add_parser("add", help="register a candidate submission")
    add.add_argument("project", type=Path)
    add.add_argument("--submission", required=True)
    add.add_argument("--label", required=True)
    add.add_argument("--hypothesis", required=True)
    add.add_argument("--parent")
    evaluate = commands.add_parser("evaluate", help="evaluate recorded artifacts without executing code")
    evaluate.add_argument("project", type=Path)
    evaluate.add_argument("--candidate", required=True)
    evaluate.add_argument("--benchmark-case", type=Path)
    select = commands.add_parser("select", help="select the strongest eligible candidate")
    select.add_argument("project", type=Path)
    status = commands.add_parser("status", help="show current tree state")
    status.add_argument("project", type=Path)
    status.add_argument("--json", action="store_true")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    try:
        if args.command == "init":
            tree = initialize_tree(args.project, args.objective_metric, args.direction, args.validation_metric, args.max_candidates, args.max_depth)
            print(f"initialized candidate tree with limit={tree['max_candidates']} depth={tree['max_depth']}")
        elif args.command == "add":
            node = add_candidate(args.project, args.submission, args.label, args.hypothesis, args.parent)
            print(f"registered {node['candidate_id']}: {node['label']}")
        elif args.command == "evaluate":
            node = evaluate_candidate(args.project, args.candidate, args.benchmark_case)
            print(f"{node['candidate_id']}: {node['status']}")
            return 0 if node["evaluation"]["eligible"] else 1
        elif args.command == "select":
            node = select_candidate(args.project)
            print(f"selected {node['candidate_id']}: {node['label']}")
        else:
            tree = get_tree(args.project)
            if args.json:
                print(json.dumps(tree, ensure_ascii=False, indent=2, sort_keys=True, allow_nan=False))
            else:
                print(f"candidates={len(tree['nodes'])} selected={tree['selected_candidate_id'] or 'none'}")
        return 0
    except (TreeError, OSError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
