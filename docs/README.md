# Documentation Guide

Use this page to distinguish implemented alpha behavior, target architecture,
human-readable guidance, templates, and research drafts.

## Start Here

- [Business Purpose](BUSINESS_PURPOSE.md) explains the problem, intended users,
  value hypothesis, and proof milestones.
- [Target Architecture](ARCHITECTURE.md) describes the planned institutional
  governance harness, trust boundaries, governance graph, and decision flow.
- [Safety Model](SAFETY_MODEL.md) defines the instruction hierarchy, safety
  invariants, threat model, and intended decision outcomes.
- [Roadmap](../ROADMAP.md) separates implemented foundation work from planned
  policy compilation, enforcement, evidence, and behavioral evaluation.

## Implemented Alpha

- [`SystemPrompt.xml`](../SystemPrompt.xml) is the canonical alpha governance
  baseline.
- [`agent_governance/`](../agent_governance/) contains the parser, validator,
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

## Governance Guidance

- [Glossary](../Glossary.md)
- [GRC Framework](../Standards/GRCFramework.md)
- [Decision-Making Standard](../Standards/Standards_Decision-Making.md)
- [Documentation Standard](../Standards/Standards_Documentation.md)
- [Operating Standard](../Standards/Standards_Operating.md)
- [Monitoring and Improvement Standard](../Standards/MonitoringImprovement.md)
- [Action and Compliance Evidence Protocols](../Standards/ActionCompliance.md)

These documents describe policy and target operating expectations. Their
presence in the repository does not mean the current package enforces them.

## Templates

- [Data Protection Policy, Standard, and Procedure](../Standards/PolicyTemplates.md)
- [Strategic Plan](../Plans/PlanTemplates_Strategy.md)
- [Risk Assessment](../Assessments/AssessmentTemplate_Risk.md)

## Research Drafts

- [Ethometric AI Responsibility Index](../Assessments/EARI.md) is explicitly an
  unvalidated measurement proposal.
- [License Warranty Proposal](../Legal/Apache3Idea.md) is a speculative research
  note. It is not the repository license and does not modify it.

The repository is distributed under the [MIT License](../LICENSE).

## Project Information

- [Contributing](../CONTRIBUTING.md)
- [Security](../SECURITY.md)
- [Roadmap](../ROADMAP.md)
