#!/usr/bin/env python3
"""Render the repository's baseline governance prompt."""

import argparse
from pathlib import Path
import sys

REPOSITORY_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPOSITORY_ROOT))

from agent_governance.prompt import generate_prompt, parse_system_prompt


def main() -> None:
    parser = argparse.ArgumentParser(description="Render a governance XML policy")
    parser.add_argument(
        "xml_path",
        nargs="?",
        default=str(REPOSITORY_ROOT / "SystemPrompt.xml"),
        help="Path to the XML policy",
    )
    args = parser.parse_args()
    print(generate_prompt(parse_system_prompt(args.xml_path)))


if __name__ == "__main__":
    main()
