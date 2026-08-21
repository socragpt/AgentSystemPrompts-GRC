# Product Charter

- **Product:** Agent Governance Harness
- **Charter version:** 0.1
- **Status:** normative project north star
- **Last reviewed:** 2026-08-21

This charter defines why the project exists, the durable principles it must
preserve, and the tests used to reject mission drift. It should change less
often than the product specification, architecture, roadmap, or implementation.

## One-Sentence Purpose

Agent Governance Harness makes organizational authority executable by deciding
whether proposed agent actions are allowed, denied, or require approval—and by
preserving evidence of the authority, policy, path, and outcome behind each
decision.

## Founding Thesis

Model alignment is necessary but insufficient for systems in which many human,
agent, and service actors pursue goals, delegate work, share resources, and
interact across organizational boundaries.

Governance is also a property of the institution around the model:

- who may authorize a goal;
- which actor may exercise a capability;
- how authority may be delegated;
- which resources and communication channels may be used;
- what constraints, approvals, and independent checks apply;
- which execution paths are acceptable; and
- what evidence must survive the decision and its outcome.

The project exists to express those relationships as portable policy, evaluate
them at a trusted decision boundary, enforce them before dispatch, and support
controlled improvement from recorded evidence.

## Problem Being Solved

When an AI system can call tools, communicate externally, alter data, spend
resources, or delegate to other agents, the central governance question is no
longer only whether its answer is good. The organization must be able to ask:

> Was this exact action authorized, through an acceptable path, under the
> applicable policy—and can we prove it?

Today those answers are usually fragmented across prompts, application code,
identity systems, manual approvals, tool permissions, policy documents, and
logs. Fragmentation makes policy inconsistent, hard to test, and difficult to
carry across models, agent frameworks, and tools.

## Product Promise

The complete harness will provide a framework-neutral control plane that:

1. represents principals, agents, services, roles, capabilities, resources,
   channels, controls, delegations, approvals, exceptions, and evidence
   requirements as a versioned governance graph;
2. validates the graph and rejects invalid, ambiguous, stale, or
   authority-amplifying relationships;
3. evaluates a normalized proposed action and returns exactly `allow`, `deny`,
   or `require_approval` with reasons, constraints, and cited controls;
4. enables a trusted enforcement point to prevent unauthorized dispatch;
5. binds approvals to the exact actor, action, parameters, policy, scope, and
   expiry they authorize;
6. records policy-linked decision and execution evidence; and
7. supports monitoring, testing, review, revision, and rollback of governance
   policy as an ongoing process.

## Adoption Promise

An organization should be able to govern its first real agent action without
replacing its agent framework, centralizing all tools behind a new vendor, or
inventing a bespoke policy engine.

The product must make adoption progressive:

1. **Model:** use a guided setup flow or starter template to describe the
   organization's actors, actions, resources, delegations, approvals, and
   constraints.
2. **Validate:** test policy locally and in continuous integration before it
   affects execution.
3. **Observe:** run decisions in shadow mode to compare proposed governance
   outcomes with existing behavior.
4. **Enforce:** place a small adapter or gateway at the tool boundary so denied
   or unresolved actions cannot dispatch.
5. **Improve:** review evidence, simulate revisions, and publish controlled
   policy updates.

One shared semantic core should support these product surfaces:

- an interactive setup wizard and configuration templates for policy owners;
- a CLI for local development, automation, simulation, and CI;
- an embedded SDK for applications that want in-process decisions;
- a local sidecar or network service for language- and framework-neutral use;
- adapters for common agent frameworks, tools, identity providers, approval
  systems, and evidence stores; and
- optional operational interfaces for policy publication, approvals,
  monitoring, and investigation.

These are delivery surfaces around one policy, decision, and evidence contract.
They must not develop incompatible governance semantics.

“Plug and play” does not mean zero organizational work. A deployment must still
identify legitimate principals, normalize governed actions, map resources and
capabilities, choose policy owners, and place enforcement where actions can
actually be intercepted. The product promise is to make that work guided,
bounded, testable, portable, and reusable.

## Intended Users

- **Builders:** AI product, platform, and infrastructure teams that need a
  reusable decision contract instead of bespoke guardrails in every agent.
- **Control owners:** security, risk, legal, compliance, and policy teams that
  need organizational requirements translated into testable behavior.
- **Operators:** workflow owners, approvers, incident responders, and auditors
  that need to understand what happened, why, and under whose authority.
- **Integrators:** framework, tool, identity, workflow, and evidence-system
  maintainers that need stable governance interfaces without adopting a
  particular model provider.

The shared job is to scale useful delegated action without scaling implicit
trust or manual oversight at the same rate.

## Governed Operating Model

The harness belongs between intent and effect:

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
tool or business-system execution
                    |
                    v
policy-linked evidence, monitoring, and revision
```

The system may use models to assist with authoring, interpretation, monitoring,
or review, but authority does not arise from a model's confidence, fluency, or
good intentions.

## Layers of Governance

The product must remain useful across three nested layers:

1. **Product:** one application contains multiple agents, subagents, tools,
   verifiers, and communication paths.
2. **Organization:** multiple teams, applications, principals, and agent groups
   operate under shared and sometimes conflicting policies.
3. **Inter-organizational:** agents and services from different policy domains
   interact without assuming that counterparties are benevolent or internally
   aligned.

The first implementation priority is product- and organization-level action
governance. Inter-organizational support should emerge through verifiable,
portable contracts and attestations—not through a requirement for one global
coordinator or universally trusted agent.

## Constitutional Principles

These principles constrain every design and implementation decision.

### 1. Legitimate authority precedes action

Every governed action must trace to an authenticated principal, authorized
goal, applicable role or delegation, and current policy. Capability must never
be inferred solely from possession of a tool or credential.

### 2. Fail closed

Missing, malformed, stale, unverifiable, conflicting, or ambiguous authority
must not become permission. Failure may produce `deny` or
`require_approval`, but never an implicit `allow`.

### 3. Delegation cannot amplify authority

A delegate cannot receive, exercise, or redelegate capability, scope, duration,
budget, or data access beyond what the delegator holds.

### 4. The path matters, not only the outcome

Success obtained through an unauthorized resource, channel, side effect, or
technique is a governance failure even when the requested result is correct.
Decisions and evidence must account for permitted execution paths.

### 5. Decision and execution are separate

Policy validation and decision generation do not dispatch an action. A trusted
enforcement point must mediate the actual capability, and it must not reinterpret
an absent or invalid decision as approval.

### 6. Trust is explicit and non-transitive

Trusting an actor, model, tool, or counterparty for one purpose does not make
all of its messages, outputs, delegates, or dependencies authoritative.
External content is data unless policy explicitly grants it instructional
authority.

### 7. Least privilege and bounded action spaces

Actors receive the narrowest capability, resource scope, data class, channel,
time window, budget, action count, and delegation depth required for the goal.
Typed interfaces and constrained channels are preferred to implicit ambient
authority.

### 8. Separation, verification, and diversity reduce correlated failure

Material actions should support independent approval, monitoring, or
verification. The design must not assume that a single powerful agent can
reliably authorize, execute, observe, and judge its own work.

### 9. Evidence is part of the control path

Every decision must produce structured evidence identifying the request,
policy version, applicable controls, outcome, constraints, and approval state.
Execution results must be linkable without exposing unnecessary sensitive data.

### 10. Governance is modular and revisable

Policies, controls, verifiers, agents, and enforcement adapters should be
replaceable and testable. The system must support review, versioning, rollback,
and improvement without requiring model retraining.

### 11. Provider and framework neutrality

Core policy and decision contracts must not depend on one model, orchestration
framework, tool vendor, or cloud. Integrations adapt to the contract rather than
define its semantics.

The CLI, wizard, SDK, service, and adapters must execute the same conformance
tests and produce equivalent decisions from equivalent normalized inputs.

### 12. Honest boundaries over inflated claims

The project must distinguish implemented behavior from target architecture,
and technical evidence from certification or legal compliance. Documentation,
examples, and naming must not imply enforcement that does not exist.

## Product Boundaries

The harness **is**:

- a policy-as-code representation of organizational authority;
- a deterministic validation and decision contract;
- a pre-dispatch governance boundary for agent actions;
- an approval-binding and evidence specification;
- an integration surface for identity, workflow, tool, and evidence systems;
  and
- an evaluation target for governance failure modes.

The harness **is not**:

- a model-training or model-alignment technique;
- an agent orchestration framework or general-purpose workflow engine;
- an identity provider, secret store, sandbox, or SIEM;
- a substitute for application security, human accountability, or legal review;
- a guarantee that every semantic deception or collusion attempt will be
  detected;
- a universal institution or centralized controller for all agents; or
- evidence of certification or regulatory compliance by itself.

It should integrate with adjacent systems rather than absorb their entire job.

## Deliberate Tradeoffs

When values conflict, the project defaults to:

- reliability and bounded authority over maximum autonomy;
- legibility and explicit contracts over implicit flexibility;
- reproducibility over context-dependent convenience;
- narrow, composable primitives over a universal policy language;
- independent verification over trust in a single node;
- data minimization over exhaustive surveillance;
- portable interfaces over vendor-specific optimization; and
- progressive adoption over an all-or-nothing platform migration;
- incremental proof over claims based on architectural intent.

These defaults may impose latency, implementation effort, or performance cost.
Exceptions require an explicit rationale and must not silently weaken the
constitutional principles.

## Measures of Product Success

The harness succeeds when an organization can answer, from deterministic
artifacts and retained evidence:

- Who authorized this goal and action?
- Which capability, resource, and channel were requested?
- Which delegation path made the actor eligible to request it?
- Which policy version and controls applied?
- Why was the action allowed, denied, or sent for approval?
- Which exact constraints and approvals bound execution?
- Did execution follow the authorized path and remain within its bounds?
- What changed when policy was revised, and can the prior decision be
  reproduced?

Adoption, integrations, and commercial value matter only if the system can
answer those questions credibly.

## Anti-Drift Test

Every material feature, integration, schema change, or public claim must answer
all of these questions before acceptance:

1. Which governed actor, workflow, or requirement does this serve?
2. How does it strengthen the path from authorized intent to decision,
   enforcement, evidence, or controlled improvement?
3. Does it preserve fail-closed behavior, least privilege, and
   non-amplifying delegation?
4. Does it make authority or trust more explicit rather than moving it into an
   opaque prompt, model judgment, or application-specific convention?
5. Is the behavior provider-neutral at the core, with vendor details confined
   to an adapter?
6. Can the behavior be tested and can its decision be explained from durable
   artifacts?
7. Does the documentation accurately distinguish what exists now from what is
   planned?
8. Does the proposal reuse the shared policy and decision semantics, or create
   a competing interpretation in a UI, SDK, service, or adapter?

A proposal is presumptively out of scope when it adds general agent
orchestration, model features, dashboards, compliance content, or integrations
without strengthening a named governance contract or proving a chartered
workflow.

## Document Authority

Use this map to prevent documents from competing silently:

1. [`PRODUCT_CHARTER.md`](PRODUCT_CHARTER.md) defines durable purpose,
   principles, and boundaries.
2. [`SAFETY_MODEL.md`](SAFETY_MODEL.md) defines safety invariants and threat
   assumptions. A conflict with the charter must be resolved explicitly before
   implementation.
3. [`PRODUCT_SPEC.md`](PRODUCT_SPEC.md) translates the charter into target
   product requirements and acceptance criteria.
4. [`POLICY_BUNDLE_V0.1.md`](POLICY_BUNDLE_V0.1.md) defines the current policy
   interchange contract.
5. [`ARCHITECTURE.md`](ARCHITECTURE.md) describes how the target system may
   satisfy the charter and product specification.
6. [`ROADMAP.md`](../ROADMAP.md) sequences delivery.
7. [`PROJECT_STATUS.md`](PROJECT_STATUS.md) records the verified current state,
   active work, and next handoff.

Architecture, roadmap, and status may evolve without changing the charter.
Changing a constitutional principle or product boundary requires an explicit
charter amendment.

## Intellectual Influence

Séb Krier's Cosmos Institute essay
[“Of Swarms and Sand Gods”](https://blog.cosmos-institute.org/p/of-swarms-and-sand-gods)
is a founding influence, not a normative specification. The project adopts its
broad framing that:

- alignment in a multi-agent world also depends on institutions, boundaries,
  rules, incentives, and mechanisms around models;
- product, organizational, and inter-organizational agent systems create
  nested governance problems;
- harnesses and verifiable protocols can reduce reliance on a counterparty's
  internal goodwill;
- constrained action and communication paths, separation of functions,
  monitoring, and modular verification can reduce classes of reward hacking;
  and
- alignment is an iterative governance process rather than a finished state.

This project turns that framing into a narrower engineering proposition:
portable authority policy, deterministic decisions, pre-dispatch enforcement,
and policy-linked evidence. It does not claim that harnesses solve alignment,
that institutional mechanisms cannot themselves fail, or that agent behavior
can be governed without ongoing human responsibility and empirical testing.

## Charter Change Control

A charter amendment must include:

- the problem or evidence motivating the change;
- the principles or boundaries affected;
- alternatives considered;
- compatibility and migration consequences;
- new tests or acceptance criteria; and
- an explicit maintainer decision recorded in project history.

Ordinary implementation work should update the product specification,
architecture, roadmap, or status rather than weakening the charter to fit a
convenient design.
