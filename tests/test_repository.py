import json
from pathlib import Path
import re
import subprocess
import sys
import tempfile
import unittest


ROOT = Path(__file__).resolve().parents[1]


class RepositoryTests(unittest.TestCase):
    def test_readme_relative_links_exist(self):
        readme = (ROOT / "README.md").read_text(encoding="utf-8")
        links = re.findall(r"\[[^]]+\]\(([^)]+)\)", readme)
        relative_links = [
            link
            for link in links
            if "://" not in link and not link.startswith("#")
        ]

        missing = [link for link in relative_links if not (ROOT / link).exists()]
        self.assertEqual([], missing)

    def test_example_runs_outside_repository(self):
        with tempfile.TemporaryDirectory() as directory:
            result = subprocess.run(
                [sys.executable, str(ROOT / "examples" / "show_agent_prompt.py")],
                cwd=directory,
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
                check=False,
                capture_output=True,
                text=True,
            )

        self.assertEqual(0, result.returncode, result.stderr)
        self.assertIn("mean_token_f1=1.000", result.stdout)


if __name__ == "__main__":
    unittest.main()
