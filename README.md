# AI Agent Governance Toolkit

An early-alpha, framework-neutral foundation for expressing organizational
governance as a multi-actor policy graph, compiling agent-facing and
decision-ready artifacts, rendering a legacy governance prompt, and running
deterministic evaluations.

> **Thesis:** Alignment in an agentic system is not only a property of the
> model. It is also a property of the institution around it: who may act, with
> which capabilities, through which channels, under which checks, and with
> what evidence.

> **Project status:** early alpha. Policy Bundle v0.1 and its deterministic
> validator/compiler are implemented; runtime authorization, approval
> workflows, and append-only decision evidence are not. Those are target
> capabilities described in the [Architecture](docs/ARCHITECTURE.md) and
> [Roadmap](ROADMAP.md).

## Purpose

Tool-using and multi-agent systems need more than broad behavioral
instructions. They need explicit authority boundaries, policy precedence,
delegation limits, communication boundaries, approval gates, resource
constraints, monitoring, and evidence requirements. This project is building
toward a portable institutional governance harness that can sit between an
agent's intent and the tools or business actions it wants to use.

The intended users are teams developing or operating AI agents that act on behalf of an organization. The toolkit is not a certification, a substitute for legal advice, or a guarantee that an AI system is safe or compliant.

## What Exists Today

- An XML governance baseline with explicit instruction precedence and
  fail-closed guidance.
- A parser, structural validator, and plain-text renderer for that baseline.
- A strict, versioned multi-actor policy-bundle schema and worked example.
- A semantic validator for references, lifecycles, delegation authority,
  approval quorum, and bounded exceptions.
- A deterministic compiler that emits `agent-policy.txt` and
  `decision-data.json` without granting runtime authorization.
- Human-readable governance standards, planning templates, and risk drafts.
- A deterministic JSONL evaluator for documentation-recall responses.
- Unit tests and continuous integration for the implemented alpha behavior.

`SystemPrompt.xml` is the canonical machine-readable policy for the current
legacy prompt workflow. [Policy Bundle v0.1](docs/POLICY_BUNDLE_V0.1.md) is the
experimental structured source for the governance-graph workflow. Neither is
a runtime security boundary.

## Target Operating Model

The target harness represents the institution in which agents act: principals,
roles, delegated authority, capabilities, resources, communication channels,
controls, approvers, monitors, and evidence requirements.

```text
authenticated principal
        -> delegated task
        -> agent proposes action
        -> governance decision
        -> deny | require approval | dispatch
        -> execution result and evidence
        -> monitoring and controlled improvement
```

Policy validation and compilation now cover the definition stage of this
flow. Runtime decisions, enforcement, approval collection, and evidence
storage remain target architecture. See the
[Architecture](docs/ARCHITECTURE.md) for the trust boundaries and design model.

## Safety Contract

The baseline policy documents these intended rules:

1. Only authorized goals may be pursued.
2. Higher-priority requirements override lower-priority instructions.
3. Agents operate with least privilege and within explicit resource limits.
4. Material, irreversible, or out-of-scope actions require approval.
5. Ambiguous or conflicting authority fails closed: stop, record the conflict, and escalate.
6. Every governed decision should produce evidence that identifies the applicable policy and outcome.

See [Safety Model](docs/SAFETY_MODEL.md) for the full hierarchy, trust boundaries, and initial threat model.

## Quick Start

The package has no runtime dependencies beyond Python 3.9 or newer.

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
python -m pip install -e .

agent-governance validate
agent-governance render
agent-governance policy validate examples/policies/multi_agent_operations.json
agent-governance policy compile examples/policies/multi_agent_operations.json --output-dir dist/policy
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
- `schemas/` – normative Policy Bundle v0.1 JSON Schema.
- `examples/policies/` – valid multi-actor policy-bundle examples.
- `docs/` – business purpose, architecture, safety model, and documentation index.
- `Standards/` – governance and operating guidance.
- `Assessments/` – risk and responsibility assessment drafts.
- `Plans/` – planning templates.
- `evals/` – datasets and deterministic evaluation runner.
- `tests/` – unit and repository-contract tests.

Start with the [Documentation Guide](docs/README.md), then see the
[Roadmap](ROADMAP.md) for planned enforcement, evidence, evaluation, and
integration milestones.

## What This Is Not

- A claim that model behavior can be made safe through prompting alone.
- A runtime authorization or sandboxing engine in its current form.
- A certification, legal opinion, or guarantee of regulatory compliance.
- A replacement for identity, security, workflow, or GRC systems.

## External Frameworks

Future control mappings will reference the NIST AI Risk Management Framework, ISO/IEC 42001, MITRE ATLAS, and OWASP guidance for agentic applications. A mapping will indicate conceptual alignment only; it will not claim certification or regulatory compliance.

## Contributing and Security

See [Contributing](CONTRIBUTING.md) before proposing changes. Report potential vulnerabilities using the process in [Security](SECURITY.md).

This project is available under the [MIT License](LICENSE).
