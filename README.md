# AI Agent Governance Toolkit

An experimental, framework-neutral toolkit for expressing organizational governance as agent-readable policy, evaluating proposed agent behavior, and producing auditable evidence.

> **Project status:** early alpha. The repository currently provides a baseline governance prompt, policy and assessment templates, a prompt renderer, and a deterministic evaluation harness. Runtime enforcement is planned but is not implemented yet.

## Purpose

Tool-using AI agents need more than broad behavioral instructions. They need explicit authority boundaries, policy precedence, approval gates, resource constraints, and evidence requirements. This project is building those capabilities as a portable governance layer that can sit between an agent's plan and the tools it wants to use.

The intended users are teams developing or operating AI agents that act on behalf of an organization. The toolkit is not a certification, a substitute for legal advice, or a guarantee that an AI system is safe or compliant.

## Safety Contract

The baseline policy follows these rules:

1. Only authorized goals may be pursued.
2. Higher-priority requirements override lower-priority instructions.
3. Agents operate with least privilege and within explicit resource limits.
4. Material, irreversible, or out-of-scope actions require approval.
5. Ambiguous or conflicting authority fails closed: stop, record the conflict, and escalate.
6. Every governed decision should produce evidence that identifies the applicable policy and outcome.

See [Safety Model](docs/SAFETY_MODEL.md) for the full hierarchy, trust boundaries, and initial threat model.

## Current Capabilities

- Parse and render the canonical baseline in `SystemPrompt.xml`.
- Validate the baseline structure and report incomplete sections.
- Provide GRC-oriented standards, plans, policies, and risk templates.
- Validate the evaluation dataset as standard JSONL.
- Score supplied model responses using normalized exact match and token F1.

The Markdown standards explain and extend the baseline. `SystemPrompt.xml` is the canonical machine-readable policy for the current alpha. A versioned policy schema and compiler are planned so generated prompts and documentation can share one structured source.

## Quick Start

The package has no runtime dependencies beyond Python 3.9 or newer.

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
python -m pip install -e .

agent-governance validate
agent-governance render
python evals/run_eval.py
python -m unittest discover -v
```

Render or validate a different XML policy:

```bash
agent-governance validate path/to/policy.xml
agent-governance render path/to/policy.xml
```

## Evaluation

`evals/grc_eval.jsonl` contains one JSON object per line with `input` and `ideal` fields. Running the evaluator without responses validates the dataset. To score responses, provide a second JSONL file containing matching `input` values and an `output` field:

```json
{"input":"According to the Glossary, what is an 'Assumption'?","output":"A belief accepted without proof."}
```

```bash
python evals/run_eval.py --responses responses.jsonl --threshold 0.70
```

These initial questions measure documentation recall, not governance compliance. Behavioral and adversarial scenarios are part of the next evaluation milestone.

## Repository Map

- `agent_governance/` – installable Python package and CLI.
- `SystemPrompt.xml` – canonical alpha policy baseline.
- `Standards/` – governance and operating guidance.
- `Assessments/` – risk and responsibility assessment drafts.
- `Plans/` – planning templates.
- `evals/` – datasets and deterministic evaluation runner.
- `tests/` – unit and repository-contract tests.

See [Roadmap](ROADMAP.md) for planned enforcement, evidence, evaluation, and integration milestones.

## External Frameworks

Future control mappings will reference the NIST AI Risk Management Framework, ISO/IEC 42001, MITRE ATLAS, and OWASP guidance for agentic applications. A mapping will indicate conceptual alignment only; it will not claim certification or regulatory compliance.

## Contributing and Security

See [Contributing](CONTRIBUTING.md) before proposing changes. Report potential vulnerabilities using the process in [Security](SECURITY.md).

This project is available under the [MIT License](LICENSE).
