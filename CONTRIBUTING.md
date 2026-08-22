# Contributing

Contributions should make the harness more explicit, testable, and
enforceable. Keep each change focused on one governance or engineering
outcome.

## Choose the Required Context

Read the root [README](README.md) and the files directly related to your
change. Additional context depends on the type of contribution.

| Change | Required context |
| --- | --- |
| Isolated documentation, test, or packaging fix | README and the affected files |
| Policy shape, validation, or compilation | [Product Charter](docs/PRODUCT_CHARTER.md), [Product Specification](docs/PRODUCT_SPEC.md), [Safety Model](docs/SAFETY_MODEL.md), and [Policy Bundle v0.1](docs/POLICY_BUNDLE_V0.1.md) |
| Action request, decision, reason code, or constraint | Product Charter, Product Specification, Safety Model, and [Decision Contract v0.1](docs/DECISION_CONTRACT_V0.1.md) |
| Architecture, roadmap, or product claim | Product Charter, Product Specification, [Project Status](docs/PROJECT_STATUS.md), and the affected design document |
| Compatibility XML behavior | Policy-change guidance below and the prompt tests |

Use the [Documentation Guide](docs/README.md) when you need a different reading
path.

## Development Setup

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
python -m pip install -e .
python -m unittest discover -s tests -v
```

## Pull Requests

1. Explain the context, objective, assumptions, risks, and compatibility
   impact.
2. Map material product behavior to requirement IDs in the
   [Product Specification](docs/PRODUCT_SPEC.md).
3. Apply and report the
   [Product Charter anti-drift test](docs/PRODUCT_CHARTER.md#anti-drift-test)
   for product behavior, contracts, architecture, and capability claims.
4. Add tests for executable behavior and examples for new public interfaces.
5. Identify each affected safety invariant or policy-precedence rule.
6. Update the README, status, or roadmap when implemented capability changes.

Normative requirements use **MUST**, **MUST NOT**, **SHOULD**, and **MAY**
deliberately. Do not change their strength as part of a language edit. Do not
describe a target feature as implemented.

## Verification

Run the relevant checks from the repository root. The complete baseline is:

```bash
python -m compileall -q src examples evals tests
agent-governance validate --strict
agent-governance policy validate examples/policies/multi_agent_operations.json
agent-governance policy evaluate \
  examples/policies/multi_agent_operations.json \
  examples/requests/browser_read_allowed.json \
  --trusted-identity-boundary identity.reference
python evals/run_eval.py
python -m unittest discover -s tests -v
```

Packaging changes also require a wheel build and an installed-wheel smoke test
from outside the repository.

## Policy Changes

Changes to `examples/legacy/SystemPrompt.xml` or the packaged copy in
`src/agent_governance/SystemPrompt.xml` must receive the same review as code.
A policy change should state its owner, intended effect, failure mode, and
evaluation method. The repository-contract test requires the two compatibility
copies to remain byte-identical.
