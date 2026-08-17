import json
from pathlib import Path
import tempfile
import unittest

from agent_governance.evaluation import (
    DatasetError,
    evaluate_responses,
    load_dataset,
    load_responses,
    token_f1,
)


ROOT = Path(__file__).resolve().parents[1]
DATASET = ROOT / "evals" / "grc_eval.jsonl"


class EvaluationTests(unittest.TestCase):
    def test_repository_dataset_is_valid_standard_jsonl(self):
        examples = load_dataset(str(DATASET))

        self.assertEqual(13, len(examples))
        self.assertEqual(13, len({example["input"] for example in examples}))

    def test_exact_response_scores_one(self):
        dataset = [{"input": "Question", "ideal": "The expected answer."}]
        responses = [{"input": "Question", "output": "the expected answer"}]

        score = evaluate_responses(dataset, responses)[0]

        self.assertTrue(score.exact_match)
        self.assertEqual(1.0, score.token_f1)

    def test_token_f1_rewards_partial_overlap(self):
        score = token_f1("policy approval is required", "approval required")

        self.assertGreater(score, 0.0)
        self.assertLess(score, 1.0)

    def test_multiline_json_object_is_rejected(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "invalid.jsonl"
            path.write_text(
                json.dumps({"input": "Question", "ideal": "Answer"}, indent=2),
                encoding="utf-8",
            )

            with self.assertRaises(DatasetError):
                load_dataset(str(path))

    def test_missing_response_is_rejected(self):
        with self.assertRaises(DatasetError):
            evaluate_responses(
                [{"input": "Question", "ideal": "Answer"}],
                [{"input": "Different question", "output": "Answer"}],
            )

    def test_response_loader_contract(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "responses.jsonl"
            path.write_text(
                json.dumps({"input": "Question", "output": "Answer"}) + "\n",
                encoding="utf-8",
            )

            self.assertEqual(1, len(load_responses(str(path))))


if __name__ == "__main__":
    unittest.main()
