import json
from pathlib import Path


def load_dataset(path: str):
    """Load evaluation dataset from a jsonl file with multi-line JSON objects."""
    data = []
    buffer = ""
    with open(path, "r", encoding="utf-8") as f:
        for line in f:
            stripped = line.strip()
            if not stripped:
                continue
            buffer += stripped
            if stripped.endswith("}"):
                data.append(json.loads(buffer))
                buffer = ""
    if buffer:
        data.append(json.loads(buffer))
    return data


def dummy_model(prompt: str) -> str:
    """Placeholder for model inference."""
    return "(model output)"


def evaluate(dataset_path: str):
    dataset = load_dataset(dataset_path)
    for example in dataset:
        response = dummy_model(example["input"])
        print("Prompt:", example["input"])
        print("Model response:", response)
        print("Ideal answer:", example["ideal"])
        print()


if __name__ == "__main__":
    eval_file = Path(__file__).with_name("grc_eval.jsonl")
    evaluate(str(eval_file))
