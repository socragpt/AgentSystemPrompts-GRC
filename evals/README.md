# GRC Evaluation Set

This directory contains a small evaluation dataset derived from the repository's documentation. The questions target definitions and concepts found in the markdown files so that language models can be evaluated on their knowledge of the GRC framework.

Each line in `grc_eval.jsonl` is a JSON object with two fields:

- `input`: the question or prompt.
- `ideal`: the expected answer based on the repository content.

The dataset can be consumed by evaluation frameworks that accept an `input` and an `ideal` field, such as [OpenAI Evals](https://github.com/openai/evals).
