"""Strict JSONL loading and deterministic response scoring."""

from collections import Counter
from dataclasses import dataclass
import json
from pathlib import Path
import re
import unicodedata
from typing import Dict, List


class DatasetError(ValueError):
    """Raised when an evaluation file does not satisfy its contract."""


@dataclass(frozen=True)
class ExampleScore:
    input: str
    ideal: str
    output: str
    exact_match: bool
    token_f1: float


def _load_jsonl(path: str, required_fields: List[str]) -> List[Dict[str, str]]:
    records: List[Dict[str, str]] = []
    source = Path(path)
    try:
        lines = source.read_text(encoding="utf-8").splitlines()
    except OSError as exc:
        raise DatasetError(f"Unable to read {source}: {exc}") from exc

    for line_number, line in enumerate(lines, 1):
        if not line.strip():
            continue
        try:
            record = json.loads(line)
        except json.JSONDecodeError as exc:
            raise DatasetError(
                f"{source}:{line_number} is not a complete JSON object: {exc.msg}"
            ) from exc
        if not isinstance(record, dict):
            raise DatasetError(f"{source}:{line_number} must contain a JSON object")
        missing = [field for field in required_fields if field not in record]
        if missing:
            raise DatasetError(
                f"{source}:{line_number} is missing fields: {', '.join(missing)}"
            )
        invalid = any(
            not isinstance(record[field], str) or not record[field].strip()
            for field in required_fields
        )
        if invalid:
            raise DatasetError(
                f"{source}:{line_number} fields must be non-empty strings"
            )
        records.append({field: record[field] for field in required_fields})

    if not records:
        raise DatasetError(f"{source} contains no examples")
    return records


def load_dataset(path: str) -> List[Dict[str, str]]:
    """Load evaluation examples containing ``input`` and ``ideal``."""

    records = _load_jsonl(path, ["input", "ideal"])
    _require_unique_inputs(records, path)
    return records


def load_responses(path: str) -> List[Dict[str, str]]:
    """Load model responses containing ``input`` and ``output``."""

    records = _load_jsonl(path, ["input", "output"])
    _require_unique_inputs(records, path)
    return records


def _require_unique_inputs(records: List[Dict[str, str]], path: str) -> None:
    seen = set()
    for record in records:
        if record["input"] in seen:
            raise DatasetError(f"{path} contains a duplicate input: {record['input']}")
        seen.add(record["input"])


def normalize(text: str) -> str:
    """Normalize text for deterministic, case-insensitive scoring."""

    normalized = unicodedata.normalize("NFKC", text).casefold()
    return " ".join(re.findall(r"[^\W_]+", normalized, flags=re.UNICODE))


def _normalized_equal(left: str, right: str) -> bool:
    left_normalized = normalize(left)
    right_normalized = normalize(right)
    if left_normalized or right_normalized:
        return left_normalized == right_normalized
    return left.strip().casefold() == right.strip().casefold()


def token_f1(ideal: str, output: str) -> float:
    """Compute bag-of-words token F1 between an ideal and output."""

    ideal_tokens = normalize(ideal).split()
    output_tokens = normalize(output).split()
    if not ideal_tokens or not output_tokens:
        return float(_normalized_equal(ideal, output))
    overlap = sum((Counter(ideal_tokens) & Counter(output_tokens)).values())
    if overlap == 0:
        return 0.0
    precision = overlap / len(output_tokens)
    recall = overlap / len(ideal_tokens)
    return 2 * precision * recall / (precision + recall)


def evaluate_responses(
    dataset: List[Dict[str, str]], responses: List[Dict[str, str]]
) -> List[ExampleScore]:
    """Match responses by input and return deterministic scores."""

    _require_unique_inputs(dataset, "dataset")
    _require_unique_inputs(responses, "responses")
    response_map = {record["input"]: record["output"] for record in responses}
    dataset_inputs = {record["input"] for record in dataset}
    missing = dataset_inputs - response_map.keys()
    extra = response_map.keys() - dataset_inputs
    if missing:
        raise DatasetError(f"Responses are missing {len(missing)} dataset inputs")
    if extra:
        raise DatasetError(f"Responses contain {len(extra)} unknown inputs")

    scores: List[ExampleScore] = []
    for example in dataset:
        output = response_map[example["input"]]
        ideal = example["ideal"]
        scores.append(
            ExampleScore(
                input=example["input"],
                ideal=ideal,
                output=output,
                exact_match=_normalized_equal(ideal, output),
                token_f1=token_f1(ideal, output),
            )
        )
    return scores
