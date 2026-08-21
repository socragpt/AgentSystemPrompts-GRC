# Documentation Guide

Use this page to distinguish implemented alpha behavior, target architecture,
human-readable guidance, templates, and research drafts.

## Start Here

- [Product Charter](PRODUCT_CHARTER.md) is the stable north star for purpose,
  principles, boundaries, tradeoffs, and the anti-drift test.
- [Product Specification](PRODUCT_SPEC.md) defines target users, workflows,
  product surfaces, deployment modes, requirement IDs, acceptance scenarios,
  and what a complete reference product means.
- [Project Status](PROJECT_STATUS.md) is the living handoff record for current
  capabilities, active work, decisions, and next priorities.
- [Decision Contract v0.1](DECISION_CONTRACT_V0.1.md) defines the implemented
  normalized request, decision, reason-code, constraint, and proposed-evidence
  contracts and their enforcement boundary.
- [Business Purpose](BUSINESS_PURPOSE.md) explains the problem, intended users,
  value hypothesis, and proof milestones.
- [Target Architecture](ARCHITECTURE.md) describes the planned institutional
  governance harness, trust boundaries, governance graph, and decision flow.
- [Safety Model](SAFETY_MODEL.md) defines the instruction hierarchy, safety
  invariants, threat model, and intended decision outcomes.
- [Roadmap](../ROADMAP.md) separates implemented policy validation and
  compilation from planned enforcement, evidence, and behavioral evaluation.

## Implemented Alpha

- [`examples/legacy/SystemPrompt.xml`](../examples/legacy/SystemPrompt.xml) is
  the compatibility XML governance baseline.
- [`src/agent_governance/`](../src/agent_governance/) contains the parser, validator,
  policy compiler, prompt renderer, evaluation functions, and command-line
  interface.
- [Policy Bundle v0.1](POLICY_BUNDLE_V0.1.md) documents the experimental
  governance graph, deterministic compilation contract, and enforcement
  boundary.
- [`schemas/policy-bundle-v0.1.schema.json`](../schemas/policy-bundle-v0.1.schema.json)
  is the normative document-shape schema; the
  [multi-agent example](../examples/policies/multi_agent_operations.json)
  exercises delegation, channel use, approval, and a bounded exception.
- [`evals/`](../evals/) contains the deterministic documentation-recall dataset
  and runner.
- [`examples/`](../examples/) contains executable usage examples.

The alpha compiler produces policy data. It does not implement runtime
authorization, approval workflows, pre-dispatch enforcement, or append-only
evidence storage.

The separate Decision Contract v0.1 evaluator returns advisory policy decisions
and proposal-only evidence. It does not authenticate callers, dispatch actions,
enforce constraints, or retain evidence.

## Governance Guidance

- [Glossary](GLOSSARY.md)
- [GRC Framework](standards/grc-framework.md)
- [Decision-Making Standard](standards/decision-making.md)
- [Documentation Standard](standards/documentation.md)
- [Operating Standard](standards/operating.md)
- [Planning Standard](standards/planning.md)
- [Monitoring and Improvement Standard](standards/monitoring-improvement.md)
- [Action and Compliance Evidence Protocols](standards/action-compliance-evidence.md)

These documents describe policy and target operating expectations. Their
presence in the repository does not mean the current package enforces them.

## Templates

- [Data Protection Policy, Standard, and Procedure](templates/policies/data-protection-policy.md)
- [Strategic Plan](templates/plans/strategic-plan.md)
- [Risk Assessment](templates/assessments/risk-assessment.md)

## Research Drafts

- [Ethometric AI Responsibility Index](research/ethometric-ai-responsibility-index.md) is explicitly an
  unvalidated measurement proposal.
- [License Warranty Proposal](research/apache-3-license-proposal.md) is a speculative research
  note. It is not the repository license and does not modify it.

The repository is distributed under the [MIT License](../LICENSE).

## Project Information

- [Product Charter](PRODUCT_CHARTER.md)
- [Product Specification](PRODUCT_SPEC.md)
- [Project Status](PROJECT_STATUS.md)
- [Agent Working Agreement](../AGENTS.md)
- [Contributing](../CONTRIBUTING.md)
- [Security](../SECURITY.md)
- [Roadmap](../ROADMAP.md)
