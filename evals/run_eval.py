#!/usr/bin/env python3
"""Validate the GRC dataset and optionally score supplied model responses."""

import argparse
from pathlib import Path
import sys
from typing import List, Optional

REPOSITORY_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPOSITORY_ROOT))

from agent_governance.evaluation import (
    DatasetError,
    evaluate_responses,
    load_dataset,
    load_responses,
)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "dataset",
        nargs="?",
        default=str(Path(__file__).with_name("grc_eval.jsonl")),
        help="JSONL dataset containing input and ideal fields",
    )
    parser.add_argument(
        "--responses",
        help="JSONL responses containing matching input and output fields",
    )
    parser.add_argument(
        "--threshold",
        type=float,
        default=0.0,
        help="minimum mean token F1 required for success (0.0 to 1.0)",
    )
    return parser


def main(argv: Optional[List[str]] = None) -> int:
    args = build_parser().parse_args(argv)
    if not 0.0 <= args.threshold <= 1.0:
        print("error: --threshold must be between 0.0 and 1.0", file=sys.stderr)
        return 2

    try:
        dataset = load_dataset(args.dataset)
        if not args.responses:
            print(f"Validated {len(dataset)} evaluation examples in {args.dataset}")
            print("Pass --responses to score model outputs.")
            return 0

        responses = load_responses(args.responses)
        scores = evaluate_responses(dataset, responses)
    except DatasetError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2

    for index, score in enumerate(scores, 1):
        print(
            f"[{index:02d}] exact={str(score.exact_match).lower()} "
            f"token_f1={score.token_f1:.3f} input={score.input}"
        )

    exact_matches = sum(score.exact_match for score in scores)
    mean_f1 = sum(score.token_f1 for score in scores) / len(scores)
    print(
        f"Summary: examples={len(scores)} exact={exact_matches} "
        f"mean_token_f1={mean_f1:.3f} threshold={args.threshold:.3f}"
    )
    return 0 if mean_f1 >= args.threshold else 1


if __name__ == "__main__":
    raise SystemExit(main())
