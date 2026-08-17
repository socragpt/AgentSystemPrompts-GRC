"""Command-line interface for prompt validation and rendering."""

import argparse
from pathlib import Path
import sys
from typing import List, Optional

from .prompt import (
    PromptValidationError,
    generate_prompt,
    parse_system_prompt,
    validate_sections,
)


def default_prompt_path() -> Path:
    """Locate the baseline in the current directory or a source checkout."""

    # Prefer the baseline associated with this source checkout. Falling back to
    # the working directory keeps non-editable installs useful while avoiding a
    # same-named local file overriding the checkout policy.
    candidates = [
        Path(__file__).resolve().parents[1] / "SystemPrompt.xml",
        Path.cwd() / "SystemPrompt.xml",
    ]
    for candidate in candidates:
        if candidate.is_file():
            return candidate
    raise PromptValidationError(
        "SystemPrompt.xml was not found; provide an explicit policy path"
    )


def _resolve_path(value: Optional[str]) -> Path:
    return Path(value) if value else default_prompt_path()


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="agent-governance",
        description="Validate or render an AI agent governance prompt",
    )
    subparsers = parser.add_subparsers(dest="command", required=True)

    validate = subparsers.add_parser("validate", help="validate an XML policy")
    validate.add_argument("xml_path", nargs="?", help="policy path")
    validate.add_argument(
        "--strict", action="store_true", help="treat structural warnings as failures"
    )

    render = subparsers.add_parser("render", help="render an XML policy as text")
    render.add_argument("xml_path", nargs="?", help="policy path")
    return parser


def main(argv: Optional[List[str]] = None) -> int:
    args = build_parser().parse_args(argv)
    try:
        path = _resolve_path(args.xml_path)
        sections = parse_system_prompt(str(path))
    except PromptValidationError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2

    warnings = validate_sections(sections)
    if args.command == "validate":
        print(f"Valid policy: {path} ({len(sections)} sections)")
        for warning in warnings:
            print(f"warning: {warning}", file=sys.stderr)
        return 1 if warnings and args.strict else 0

    print(generate_prompt(sections))
    return 0


def entrypoint() -> None:
    raise SystemExit(main())


if __name__ == "__main__":
    entrypoint()
