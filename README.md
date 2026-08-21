# Agent Governance Harness

**Policy-as-code for defining authority, delegation, approvals, and evidence
requirements in multi-agent systems.**

[![CI](https://github.com/socragpt/agent-governance-harness/actions/workflows/ci.yml/badge.svg)](https://github.com/socragpt/agent-governance-harness/actions/workflows/ci.yml)
[![License: MIT](https://img.shields.io/badge/license-MIT-blue.svg)](LICENSE)

Agent Governance Harness lets an organization describe its actors, roles,
capabilities, resources, policies, approvals, delegations, and exceptions as a
versioned governance graph. It validates that graph fail-closed and compiles it
into deterministic agent instructions and decision data, then evaluates
versioned normalized action requests against the same policy semantics.

> **Status:** early alpha. Policy Bundle v0.1, semantic validation,
> deterministic compilation, and the side-effect-free Decision Contract v0.1
> evaluator work today. Identity verification, approval collection, tool
> enforcement, and durable evidence storage do not.

## Try It in 60 Seconds

The package requires Python 3.9 or newer and has no runtime dependencies.

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -e .

agent-governance policy validate examples/policies/multi_agent_operations.json
agent-governance policy compile \
  examples/policies/multi_agent_operations.json \
  --output-dir dist/policy

agent-governance policy evaluate \
  examples/policies/multi_agent_operations.json \
  examples/requests/browser_read_allowed.json \
  --trusted-identity-boundary identity.reference
```

Successful compilation creates:

- `agent-policy.txt` — stable, agent-facing governance instructions;
- `decision-data.json` — normalized policy data, resolution rules, and source
  hashes used by the decision contract.

Compilation produces policy data. It does not authorize or dispatch an action.
The evaluator separately returns an advisory governance decision and proposed
evidence. No current component enforces that decision before dispatch.

## What It Governs

```text
actor -> role -> capability -> resource
  |                    |
  +---- delegation ----+

policy -> control -> allow | deny | require_approval
                         |
                         +-> constraints, evidence, exceptions
```

Policy Bundle v0.1 can express:

- human, agent, and service actors;
- role-based baseline authority;
- capability and resource boundaries;
- human-to-agent and agent-to-agent delegation;
- approval quorum and separation-of-duties requirements;
- policy precedence, lifecycle, provenance, and fail-closed defaults;
- constrained, time-bounded exceptions; and
- evidence fields a future runtime must retain.

The validator rejects duplicate IDs, unresolved references, invalid
lifecycles, delegation cycles, authority amplification, impossible approval
quorums, and overbroad exceptions.

## Why a Harness

Alignment in an agentic system is not only a property of the model. It is also
a property of the institution around it: who may act, with which authority,
through which channels, under which checks, and with what evidence.

The target operating flow is:

```text
authenticated principal
        -> delegated task
        -> agent proposes action
        -> governance decision
        -> deny | require approval | dispatch
        -> execution result and evidence
        -> monitoring and controlled improvement
```

This repository currently implements policy definition, compilation, and the
side-effect-free decision portion of that flow. See the
[Decision Contract v0.1](docs/DECISION_CONTRACT_V0.1.md),
[architecture](docs/ARCHITECTURE.md), and [roadmap](ROADMAP.md) for the
enforcement path.

The [Product Charter](docs/PRODUCT_CHARTER.md) is the durable statement of
purpose and anti-drift test. The [Product Specification](docs/PRODUCT_SPEC.md)
translates it into target workflows, requirement IDs, and acceptance scenarios.
The target delivery model is one shared governance engine exposed through a
guided initializer, CLI, embedded SDK, service, and enforcement adapters. Only
the policy CLI/compiler and shared Python SDK/CLI decision evaluator are
implemented in the current alpha.

## Safety Contract

The project is designed around these invariants:

1. Only authorized goals may be pursued.
2. Higher-priority requirements override lower-priority instructions.
3. Actors operate with least privilege and explicit resource limits.
4. Material, irreversible, or out-of-scope actions require approval.
5. Missing, stale, ambiguous, or conflicting authority fails closed.
6. Governed decisions identify the applicable policy and controls.
7. Delegation cannot create authority the delegator does not possess.

See the [safety model](docs/SAFETY_MODEL.md) for the instruction hierarchy,
trust boundaries, and threat model.

## Legacy XML Workflow

The original XML governance prompt remains available as a compatibility
example in [`examples/legacy/`](examples/legacy/). The installed package ships
the same baseline, so these commands work without a repository checkout:

```bash
agent-governance validate --strict
agent-governance render
```

Policy Bundle v0.1 is the structured path forward. The XML prompt is not a
runtime security boundary.

## Documentation-Recall Evaluation

The separate evaluation utility measures documentation recall using exact match
and token F1:

```bash
python evals/run_eval.py
python evals/run_eval.py --responses responses.jsonl --threshold 0.70
```

These checks do not establish governance compliance. Behavioral and
adversarial scenarios are planned in the [roadmap](ROADMAP.md).

## Repository Map

- `src/agent_governance/` — installable library and `agent-governance` CLI.
- `schemas/` — normative policy, request, decision, and evidence JSON Schemas.
- `conformance/` — shared decision cases for SDK, CLI, and future service surfaces.
- `examples/policies/` — valid multi-actor governance bundles.
- `examples/requests/` — allow, deny, and approval-gated Action Request v0.1 examples.
- `examples/legacy/` — the compatibility XML prompt baseline.
- `docs/` — architecture, safety, standards, templates, and research.
- `evals/` — deterministic evaluation datasets and runner.
- `tests/` — unit and repository-contract tests.

Start with the [Product Charter](docs/PRODUCT_CHARTER.md), the
[Product Specification](docs/PRODUCT_SPEC.md), the
[documentation guide](docs/README.md), the
[Policy Bundle v0.1 specification](docs/POLICY_BUNDLE_V0.1.md), the
[Decision Contract v0.1](docs/DECISION_CONTRACT_V0.1.md), and the
[business purpose](docs/BUSINESS_PURPOSE.md).

## Boundaries

This project is not:

- a claim that prompting alone makes model behavior safe;
- an identity provider, action dispatcher, enforcement point, or sandbox in its
  current form;
- a certification, legal opinion, or guarantee of regulatory compliance; or
- a replacement for identity, security, workflow, or GRC systems.

Future control mappings may reference established governance and security
frameworks, but mappings indicate conceptual alignment rather than
certification.

See [Contributing](CONTRIBUTING.md) before proposing changes and
[Security](SECURITY.md) for vulnerability reporting. The project is available
under the [MIT License](LICENSE).
