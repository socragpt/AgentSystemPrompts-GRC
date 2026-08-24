# Agent Governance Harness

**Policy-as-code for authority, delegation, approvals, and evidence requirements
in multi-agent systems.**

[![CI](https://github.com/socragpt/agent-governance-harness/actions/workflows/ci.yml/badge.svg)](https://github.com/socragpt/agent-governance-harness/actions/workflows/ci.yml)
[![License: MIT](https://img.shields.io/badge/license-MIT-blue.svg)](LICENSE)

Agent Governance Harness evaluates a normalized proposed action against a
versioned governance policy. It returns exactly `allow`, `deny`, or
`require_approval`, with reasons, effective constraints, policy provenance, and
a proposal-only evidence record.

> **Status:** early alpha. Policy Bundle v0.1, semantic validation,
> deterministic compilation, and the side-effect-free Decision Contract v0.1
> evaluator are implemented. Dogfood 0 Phase 1 and local observation
> hardening are implemented, and the non-enforcing repository-development
> shadow pilot is active. Identity
> verification, approval-grant verification, pre-dispatch enforcement, and
> durable evidence storage are not.

## Run the Current Alpha

The package requires Python 3.9 or newer and has no runtime dependencies.

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -e .

agent-governance policy validate examples/policies/multi_agent_operations.json
agent-governance policy evaluate \
  examples/policies/multi_agent_operations.json \
  examples/requests/browser_read_allowed.json \
  --trusted-identity-boundary identity.reference
```

The evaluation command returns Decision Result v0.1 JSON. It does not dispatch
or block the proposed action.

To compile the policy into deterministic artifacts:

```bash
agent-governance policy compile \
  examples/policies/multi_agent_operations.json \
  --output-dir dist/policy
```

Compilation creates:

- `agent-policy.txt`, which contains stable agent-facing governance
  instructions; and
- `decision-data.json`, which contains normalized policy data, resolution
  rules, and source hashes.

These artifacts are policy data. They are not execution authorization.

## What Works Now

The current alpha can:

- represent human, agent, and service actors, roles, capabilities, resources,
  controls, approval requirements, delegations, exceptions, and evidence
  requirements.
- reject broken references, invalid lifecycles, delegation cycles, authority
  amplification, impossible approval quorums, and overbroad exceptions.
- compile equivalent policy input into equivalent artifacts.
- evaluate Action Request v0.1 with fail-closed behavior.
- resolve policy effects as `deny > require_approval > allow` at equal
  precedence.
- return cited controls, authority paths, effective constraints, stable reason
  codes, and policy provenance.
- expose the same evaluator through the Python SDK and CLI.
- validate deterministic repository-development shadow scenarios, create
  minimized local pilot records, and verify aggregate pilot metrics without
  enforcing actions.

The current alpha cannot:

- authenticate or cryptographically verify identity assertions.
- create, collect, verify, revoke, or consume approval grants.
- prevent a tool, API, or agent framework from dispatching an action.
- enforce returned constraints during execution.
- retain append-only or tamper-evident evidence.

## Choose a Documentation Path

| Goal | Start here |
| --- | --- |
| Understand or author policy | [Policy Bundle v0.1](docs/POLICY_BUNDLE_V0.1.md) and the [example policy](examples/policies/multi_agent_operations.json) |
| Integrate the evaluator | [Decision Contract v0.1](docs/DECISION_CONTRACT_V0.1.md) and the [conformance fixture](conformance/decision-contract-v0.1.json) |
| Review active dogfood evidence | [Dogfood 0 Pilot Report](docs/DOGFOOD_REPORT.md) |
| Contribute code or documentation | [Contributing](CONTRIBUTING.md) |
| Understand product direction | [Product Charter](docs/PRODUCT_CHARTER.md), [Product Specification](docs/PRODUCT_SPEC.md), and [Project Status](docs/PROJECT_STATUS.md) |
| Browse all documentation | [Documentation Guide](docs/README.md) |

## Governance Boundary

The target product belongs between intent and effect:

```text
authenticated principal and authorized goal
                    |
                    v
agent or service proposes a normalized action
                    |
                    v
policy decision: deny | require_approval | allow
                    |
                    v
trusted pre-dispatch enforcement point
                    |
                    v
tool execution and policy-linked evidence
```

This repository currently implements policy definition, compilation, and the
side-effect-free decision portion of that flow. See the
[architecture](docs/ARCHITECTURE.md) and [roadmap](ROADMAP.md) for the target
enforcement path.

## Repository Map

- `src/agent_governance/` contains the installable library and
  `agent-governance` CLI.
- `schemas/` contains the normative v0.1 JSON Schemas.
- `conformance/` contains shared decision cases for current and future product
  surfaces.
- `dogfood/` contains the non-enforcing repository-development shadow pilot.
- `examples/policies/` and `examples/requests/` contain executable examples.
- `tests/` contains policy, decision, CLI, and repository-contract tests.
- `docs/` contains product contracts, architecture, project status, reference
  guidance, templates, and research drafts.

## Compatibility and Experimental Material

The original XML prompt remains a compatibility example in
[`examples/legacy/`](examples/legacy/). The installed package ships the same
baseline, so these commands remain available:

```bash
agent-governance validate --strict
agent-governance render
```

The XML prompt is not a runtime security boundary. Policy Bundle v0.1 is the
structured path forward.

The separate documentation-recall utility under [`evals/`](evals/) measures
exact match and token F1. It does not test agent behavior or establish
governance compliance. Behavioral and adversarial evaluation remains planned.

## Scope and Safety

The project is not an identity provider, action dispatcher, sandbox, agent
framework, certification, legal opinion, or guarantee of regulatory
compliance. The harness must fail closed if authority is missing, stale,
malformed, ambiguous, or conflicting. Delegation must not create authority that
the delegator does not possess.

See the [Safety Model](docs/SAFETY_MODEL.md), [Security Policy](SECURITY.md), and
[MIT License](LICENSE).
