# Business Purpose

## Govern the action, not just the answer

Agent Governance Harness is intended to become a policy-and-evidence
control layer for tool-using AI agents. Its business purpose is to help
organizations authorize autonomous actions, enforce explicit constraints, and
retain evidence explaining what happened and why.

The project is currently an early alpha. It provides a governance baseline,
an experimental multi-actor policy schema, a deterministic validator and
compiler, policy and assessment templates, a command-line interface, and an
evaluation harness. Runtime enforcement, approval workflows, and append-only
decision evidence are planned capabilities, not current production features.

## The business problem

When a model can call tools, change data, move work, spend resources, or
communicate externally, AI risk becomes operating risk. The central business
question changes from “Was the answer acceptable?” to:

> Was the action authorized, and can the organization prove it?

Most current controls are fragmented across prompts, application-specific
guardrails, manual approvals, policy documents, and logs. Operational
governance requires a shared contract that can express:

- explicit authority boundaries;
- enforceable resource and data constraints;
- approval gates for material actions;
- predictable handling of ambiguous or conflicting instructions; and
- evidence tied to the policy and authority behind each decision.

## Who it serves

The harness addresses a shared accountability problem across three groups:

- **Build:** AI product and platform teams need reusable governance instead of
  hard-coding policy separately into every agent.
- **Control:** Security, risk, legal, and compliance teams need organizational
  policy translated into testable decisions.
- **Operate:** Operations and audit teams need to see what happened, why it
  happened, and under whose authority.

Their shared job is to scale useful agent action without scaling manual
oversight at the same rate.

## Intended product role

The target operating model places governance between an agent's intent and the
tool or business action it wants to perform:

1. An agent proposes an action.
2. A governance decision evaluates policy, context, and delegated authority.
3. The decision returns `allow`, `deny`, or `require_approval`.
4. An allowed or approved action may proceed to the relevant tool or business
   system.
5. The system records evidence identifying the policy version, applicable
   controls, disposition, approval, and execution result.

This layer is intended to remain provider-neutral so one governance contract
can serve multiple agents, models, orchestration frameworks, and tools.

## Business value hypothesis

If the planned control layer is implemented and validated, it could create
value in four ways:

- **Faster deployment:** Reuse policy and approval logic across agent projects
  instead of rebuilding governance each time.
- **Consistent control:** Apply the same authority and constraint rules across
  models, tools, and operating teams.
- **Audit-ready evidence:** Record which policy governed a decision, its
  disposition, any approval, and the execution result.
- **Lower switching cost:** Keep governance portable when models, agent
  frameworks, or tool stacks change.

These are product hypotheses to test, not claims about the alpha's current
performance.

## Differentiation

The harness does not need to replace the model, agent framework, security
product, or governance, risk, and compliance system. Those products typically
optimize a single layer. The harness's proposed differentiation is connective
tissue across them:

- authority checked before execution;
- policy compiled into deterministic decision data;
- evidence tied to policy versions and approvals; and
- portable controls that can follow the organization across its AI stack.

The defensible capability is making governance executable and testable, rather
than leaving it only as documentation or application-specific logic.

## Commercial hypothesis

Any commercial model remains to be validated with users and design partners. A
possible path is:

- **Open core:** Policy schemas, CLI and compiler, baseline controls, and an
  evaluation harness earn adoption, scrutiny, and trust.
- **Enterprise layer:** A policy registry, approval workflows, system
  integrations, and evidence retention support subscription or managed
  deployment offerings.
- **Services and content:** Control packs, implementation support, assurance
  reporting, and partner enablement support projects and packaged intellectual
  property.

This framing is a proposed business model, not a statement of current pricing,
revenue, or product tiers.

## Proof milestones

Earn the business case through technical proof:

1. **Define — policy specification and compiler (v0.1 implemented).** Versioned
   schemas and a deterministic compiler. Invalid policy fails at a precise
   location, and identical input produces identical artifacts.
2. **Decide — decision and evidence proposal (v0.1 implemented).** Normalized
   requests return `allow`, `deny`, or `require_approval` with stable reasons,
   controls, constraints, provenance, and proposal-only evidence.
3. **Observe — repository-development dogfood pilot (complete).** The pilot
   applied the current decision contract in explicitly non-enforcing shadow
   mode to 25 material actions. Its evidence selected the next product build.
4. **Enforce — approval and pre-dispatch reference.** The selected first step
   is an exact-bound Approval Grant v0.1 contract and verifier. A later trusted
   adapter must demonstrate that denied or unresolved actions cannot dispatch
   and that execution remains within returned constraints.
5. **Prove — behavioral evaluation and integration.** Adversarial evaluations
   and an end-to-end agent integration demonstrate that continuous integration
   can detect meaningful governance regressions before release.

The immediate next proof is Approval Grant v0.1. The completed
[Repository Development Dogfooding Plan](DOGFOOD_PLAN.md) recorded 31
reproducible observations, including 25 material actions. Approval remained
unresolved in 14 observations, or 45.2%, so the next milestone will define and
verify exact-bound grants before a pre-dispatch adapter is attempted. This work
will not claim approval collection, dispatch, enforcement, or trusted evidence
retention.

## Boundaries

The harness is not a certification, a substitute for legal advice, or a
guarantee that an AI system is safe or compliant. Future mappings to external
governance and security frameworks would indicate conceptual alignment only.

For the durable product contract, see the [Product Charter](PRODUCT_CHARTER.md)
and [Product Specification](PRODUCT_SPEC.md). For current implementation and
delivery state, see the [README](../README.md), [Safety Model](SAFETY_MODEL.md),
[Project Status](PROJECT_STATUS.md), and [Roadmap](../ROADMAP.md).
