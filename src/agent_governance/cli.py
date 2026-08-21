"""Command-line interface for prompt and policy-bundle workflows."""

import argparse
from importlib import resources
import json
from pathlib import Path
import sys
from typing import List, Optional

from .policy import (
    PolicyBundleError,
    load_policy_bundle,
    validate_policy_bundle,
    validation_result,
    write_compiled_policy,
)
from .prompt import (
    PromptValidationError,
    generate_prompt,
    parse_system_prompt,
    validate_sections,
)


def default_prompt_path() -> Path:
    """Locate the baseline distributed with the installed package."""

    candidate = resources.files("agent_governance").joinpath("SystemPrompt.xml")
    if candidate.is_file():
        return Path(str(candidate))
    raise PromptValidationError(
        "The packaged SystemPrompt.xml was not found; provide an explicit policy path"
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

    policy = subparsers.add_parser(
        "policy", help="validate or compile a Policy Bundle v0.1 document"
    )
    policy_commands = policy.add_subparsers(dest="policy_command", required=True)
    policy_validate = policy_commands.add_parser(
        "validate", help="validate a JSON policy bundle"
    )
    policy_validate.add_argument("policy_path", help="policy bundle path")
    policy_validate.add_argument(
        "--format",
        choices=("text", "json"),
        default="text",
        help="validation output format",
    )
    policy_compile = policy_commands.add_parser(
        "compile", help="compile a valid policy bundle"
    )
    policy_compile.add_argument("policy_path", help="policy bundle path")
    policy_compile.add_argument(
        "--output-dir", required=True, help="artifact destination directory"
    )
    return parser


def _policy_main(args: argparse.Namespace) -> int:
    try:
        bundle = load_policy_bundle(args.policy_path)
    except PolicyBundleError as exc:
        if getattr(args, "format", "text") == "json":
            print(json.dumps(validation_result(exc.issues), indent=2, sort_keys=True))
        else:
            for issue in exc.issues:
                print(
                    f"error [{issue.code}] {issue.path}: {issue.message}",
                    file=sys.stderr,
                )
        return 2

    issues = validate_policy_bundle(bundle)
    if args.policy_command == "validate":
        if args.format == "json":
            print(json.dumps(validation_result(issues), indent=2, sort_keys=True))
        elif issues:
            for issue in issues:
                related = f" (see {issue.related_path})" if issue.related_path else ""
                print(
                    f"error [{issue.code}] {issue.path}: {issue.message}{related}",
                    file=sys.stderr,
                )
        else:
            print(f"Valid policy bundle: {args.policy_path}")
        return 2 if issues else 0

    try:
        text_path, data_path = write_compiled_policy(bundle, args.output_dir)
    except PolicyBundleError as exc:
        for issue in exc.issues:
            related = f" (see {issue.related_path})" if issue.related_path else ""
            print(
                f"error [{issue.code}] {issue.path}: {issue.message}{related}",
                file=sys.stderr,
            )
        return 2
    except OSError as exc:
        print(f"error: unable to write compiled policy: {exc}", file=sys.stderr)
        return 2
    print(f"Wrote {text_path}")
    print(f"Wrote {data_path}")
    return 0


def _prompt_main(args: argparse.Namespace) -> int:
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

    if warnings:
        for warning in warnings:
            print(f"error: {warning}", file=sys.stderr)
        return 1
    print(generate_prompt(sections))
    return 0


def main(argv: Optional[List[str]] = None) -> int:
    args = build_parser().parse_args(argv)
    if args.command == "policy":
        return _policy_main(args)
    return _prompt_main(args)


def entrypoint() -> None:
    raise SystemExit(main())


if __name__ == "__main__":
    entrypoint()
