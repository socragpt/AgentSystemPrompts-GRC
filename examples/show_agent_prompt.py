#!/usr/bin/env python3
"""Example CLI to load SystemPrompt.xml and outline agent actions."""
import argparse
from pathlib import Path
import sys

# Allow imports from the repository root when executed as a script
sys.path.append(str(Path(__file__).resolve().parents[1]))

from utils.agent_utils import parse_system_prompt, generate_prompt


def main() -> None:
    parser = argparse.ArgumentParser(description="Render a prompt from SystemPrompt.xml")
    parser.add_argument(
        "xml_path",
        nargs="?",
        default="SystemPrompt.xml",
        help="Path to the SystemPrompt.xml file",
    )
    args = parser.parse_args()

    xml_file = Path(args.xml_path)
    sections = parse_system_prompt(str(xml_file))
    prompt_text = generate_prompt(sections)

    print(prompt_text)


if __name__ == "__main__":
    main()
