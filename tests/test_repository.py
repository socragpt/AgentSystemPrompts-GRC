import json
import os
from pathlib import Path
import re
import subprocess
import sys
import tempfile
import unittest


ROOT = Path(__file__).resolve().parents[1]


class RepositoryTests(unittest.TestCase):
    def test_root_contains_only_current_product_surfaces(self):
        retired_root_paths = [
            "Assessments",
            "Legal",
            "Plans",
            "Standards",
            "Glossary.md",
            "SystemPrompt.xml",
            "agent_governance",
            "utils",
        ]

        unexpected = [
            path for path in retired_root_paths if (ROOT / path).exists()
        ]
        self.assertEqual([], unexpected)

    def test_packaged_policy_matches_canonical_policy(self):
        canonical = ROOT / "examples" / "legacy" / "SystemPrompt.xml"
        packaged = ROOT / "src" / "agent_governance" / "SystemPrompt.xml"

        self.assertEqual(canonical.read_bytes(), packaged.read_bytes())

    def test_markdown_relative_links_exist(self):
        missing = []
        for document in ROOT.rglob("*.md"):
            relative_document = document.relative_to(ROOT)
            if any(
                part.startswith(".")
                or part == "build"
                or part.endswith(".egg-info")
                for part in relative_document.parts
            ):
                continue
            links = re.findall(
                r"\[[^]]+\]\(([^)]+)\)", document.read_text(encoding="utf-8")
            )
            for link in links:
                target = link.split("#", 1)[0]
                if not target or "://" in target or target.startswith("mailto:"):
                    continue
                if not (document.parent / target).exists():
                    missing.append(f"{relative_document}: {link}")
        self.assertEqual([], missing)

    def test_example_runs_outside_repository(self):
        with tempfile.TemporaryDirectory() as directory:
            result = subprocess.run(
                [sys.executable, str(ROOT / "examples" / "show_agent_prompt.py")],
                cwd=directory,
                env={**os.environ, "PYTHONPATH": str(ROOT / "src")},
                check=False,
                capture_output=True,
                text=True,
            )

        self.assertEqual(0, result.returncode, result.stderr)
        self.assertIn("# Instruction Precedence", result.stdout)

    def test_evaluation_cli_scores_responses(self):
        with tempfile.TemporaryDirectory() as directory:
            temporary = Path(directory)
            dataset = temporary / "dataset.jsonl"
            responses = temporary / "responses.jsonl"
            dataset.write_text(
                json.dumps({"input": "Question", "ideal": "Expected answer"}) + "\n",
                encoding="utf-8",
            )
            responses.write_text(
                json.dumps({"input": "Question", "output": "expected answer"}) + "\n",
                encoding="utf-8",
            )
            result = subprocess.run(
                [
                    sys.executable,
                    str(ROOT / "evals" / "run_eval.py"),
                    str(dataset),
                    "--responses",
                    str(responses),
                    "--threshold",
                    "1.0",
                ],
                cwd=directory,
                env={**os.environ, "PYTHONPATH": str(ROOT / "src")},
                check=False,
                capture_output=True,
                text=True,
            )

        self.assertEqual(0, result.returncode, result.stderr)
        self.assertIn("mean_token_f1=1.000", result.stdout)


if __name__ == "__main__":
    unittest.main()
