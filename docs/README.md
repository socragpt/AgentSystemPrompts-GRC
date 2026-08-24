# Documentation Guide

Choose the shortest path that matches your work. You do not need to read every
project document before you use or contribute to the current alpha.

## First-Time User

Start with the root [README](../README.md). It contains the implemented product
boundary and a verified policy-evaluation quickstart.

Then inspect these executable examples:

- [multi-agent policy](../examples/policies/multi_agent_operations.json).
- [allowed browser request](../examples/requests/browser_read_allowed.json).
- [approval-gated email request](../examples/requests/email_send_requires_approval.json).
- [valid exact-bound approval grant](../examples/approvals/valid.json).
- [denied unmapped request](../examples/requests/unmapped_action_denied.json).

The evaluator returns an advisory governance decision and proposal-only
evidence. No current component prevents dispatch.

## Policy Author

Read these files:

1. [Policy Bundle v0.1](POLICY_BUNDLE_V0.1.md) for the policy contract,
   validation rules, and deterministic compilation behavior.
2. The normative
   [Policy Bundle JSON Schema](../schemas/policy-bundle-v0.1.schema.json).
3. The [multi-agent policy](../examples/policies/multi_agent_operations.json)
   for a complete example.

Use the [Safety Model](SAFETY_MODEL.md) when policy work changes authority,
delegation, approval, or failure behavior.

## SDK or Integration Developer

Read these files:

1. [Decision Contract v0.1](DECISION_CONTRACT_V0.1.md) for request, decision,
   reason-code, constraint, and proposed-evidence semantics.
2. [Approval Grant v0.1](APPROVAL_GRANT_V0.1.md) for exact binding,
   caller-supplied verification state, approver, and fail-closed semantics.
3. The [Action Request](../schemas/action-request-v0.1.schema.json),
   [Decision Result](../schemas/decision-result-v0.1.schema.json), and
   [Proposed Evidence Record](../schemas/proposed-evidence-record-v0.1.schema.json)
   JSON Schemas.
4. The normative [Approval Grant](../schemas/approval-grant-v0.1.schema.json),
   [Approval Verification State](../schemas/approval-verification-state-v0.1.schema.json),
   and [Approval Verification Result](../schemas/approval-verification-result-v0.1.schema.json)
   JSON Schemas.
5. The shared [decision](../conformance/decision-contract-v0.1.json) and
   [approval](../conformance/approval-grant-v0.1.json) conformance fixtures.

The Python SDK and CLI use one decision evaluator and one approval verifier.
Future services and adapters must use the same semantics and conformance cases.

## Dogfood Operator

Read the [Dogfood 0 procedure](../dogfood/README.md) to reproduce the completed
repository-development pilot or run separately scoped follow-up observations.
The pilot provides deterministic fixtures, a local v0.2 recorder, and a
verifier/reporter that retains v0.1 read compatibility. Keep live records in
the ignored pilot directory or outside the repository. The historical live
gate did not authorize development actions or enforcement.

Read the [Dogfood 0 Pilot Report](DOGFOOD_REPORT.md) for the final sanitized
metrics, findings, evidence limits, ranked gaps, and selected next milestone.

## Contributor

Read [Contributing](../CONTRIBUTING.md) first. It identifies the context and
verification required for each type of change.

Read the deeper product documents before you change governance behavior,
public contracts, capability claims, or product direction:

- [Product Charter](PRODUCT_CHARTER.md) defines durable purpose, principles,
  boundaries, and the anti-drift test.
- [Product Specification](PRODUCT_SPEC.md) defines target workflows,
  requirement IDs, and acceptance scenarios.
- [Safety Model](SAFETY_MODEL.md) defines safety invariants and threat
  assumptions.
- [Target Architecture](ARCHITECTURE.md) describes the planned system design.
- [Project Status](PROJECT_STATUS.md) records verified current behavior and the
  next recommended milestone.
- [Repository Development Dogfooding Plan](DOGFOOD_PLAN.md) defines the
  non-enforcing shadow pilot and its next-build decision rules.
- [Dogfood 0 Pilot Report](DOGFOOD_REPORT.md) records sanitized pilot evidence
  and the final next-build decision.
- [Roadmap](../ROADMAP.md) sequences planned delivery.

## Document Authority

When documents appear to overlap, use this order:

1. The Product Charter defines durable purpose and boundaries.
2. The Safety Model defines safety invariants and threat assumptions.
3. The Product Specification defines target requirements.
4. Policy Bundle v0.1, Decision Contract v0.1, and Approval Grant v0.1 define
   implemented public contracts.
5. Architecture and Roadmap describe the target design and delivery sequence.
6. Project Status records the verified current state.
7. The Dogfooding Plan defines one completed experiment. It does not change
   the product contract.

Implementation and tests are authoritative when a current-state document
disagrees with executable behavior.

## Secondary and Compatibility Material

These files are not required for the primary developer path:

- [`examples/legacy/SystemPrompt.xml`](../examples/legacy/SystemPrompt.xml) is
  the shipped XML compatibility baseline. It is not an enforcement boundary.
- [Business Purpose](BUSINESS_PURPOSE.md) records the value and commercial
  hypotheses behind the target product.
- [Glossary](GLOSSARY.md) defines project and governance terms.
- [`standards/`](standards/) contains human-readable organizational guidance.
  The package does not enforce these documents.
- [`templates/`](templates/) contains general planning, policy, and risk
  templates. They are not Policy Bundle v0.1 starter policies.
- [`research/`](research/) contains speculative or unvalidated drafts. Research
  content is not a product contract.
- [`evals/`](../evals/) contains a documentation-recall experiment. It does not
  test governance enforcement or agent behavior.

The repository uses the [MIT License](../LICENSE). The research license note
does not modify the repository license.

## Agent Instructions

[AGENTS.md](../AGENTS.md) contains task-routing and continuity instructions for
coding agents. Human contributors can use the documentation paths above.
