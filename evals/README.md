# GRC Evaluation Set

This directory contains a small evaluation dataset derived from the repository's documentation. The questions target definitions and concepts found in the markdown files so that language models can be evaluated on their knowledge of the GRC framework.

Each line in `grc_eval.jsonl` is a complete JSON object with two fields:

- `input`: the question or prompt.
- `ideal`: the expected answer based on the repository content.

Validate the dataset with:

```bash
python evals/run_eval.py
```

To score model output, supply a JSONL file containing matching `input` values and an `output` field:

```bash
python evals/run_eval.py --responses responses.jsonl --threshold 0.70
```

The runner reports normalized exact match and token F1. These metrics are deterministic baseline checks; they are not a substitute for human review or behavioral safety evaluation.
