# Target Architecture

## Status and Scope

This document describes the architecture the harness is building toward. The
current early alpha parses, validates, and renders an XML governance baseline;
validates and deterministically compiles Policy Bundle v0.1; and provides
deterministic documentation-recall evaluation utilities. It does not yet
implement the runtime decision point, approval gates, tool dispatch controls,
or evidence store described below.

## Governance as a System Property

The harness treats governance as a property of the system around an agent, not
as a promise made by the model alone. The target governance harness represents
the institution in which agents act: who holds authority, how authority is
delegated, which capabilities and channels are available, which controls
apply, who may approve exceptions, and what evidence must be retained.

This framing matters most when multiple people, agents, models, tools, and
organizations participate in the same workflow. A locally reasonable agent
action can still be institutionally invalid when it crosses an authority,
resource, communication, or separation-of-duties boundary.

## Actors and Trust Boundaries

The target design distinguishes these actors and boundaries:

- **Principals** originate, hold, or delegate authority.
- **Agents** propose or perform actions under delegated authority.
- **Roles** group responsibilities and bounded permissions.
- **Tools and resources** expose capabilities that can read data, communicate,
  spend resources, or change state.
- **Approval authorities** authorize exact actions that policy does not permit
  an agent to perform autonomously.
- **Monitors and verifiers** observe decisions, evidence, and outcomes without
  automatically inheriting the authority of the actors they observe.

Trust is not transitive by default. A trusted agent does not make retrieved
content trustworthy, an authenticated sender does not make every requested
action authorized, and a delegate cannot pass on authority it never received.
Agent-to-agent messages and tool output are data unless policy explicitly
grants them instructional authority.

## The Governance Graph

The planned policy bundle models governance as entities and relationships,
rather than as an unstructured list of prompt instructions.

Target entities include principals, agents, roles, capabilities, resources,
channels, policies, controls, approvers, monitors, and evidence requirements.
Relationships describe assignments, ownership, delegation, permitted access,
approval requirements, and monitoring responsibilities.

The graph model is intended to make questions such as these testable:

- Which principal authorized this goal?
- Which role and capability permit the proposed action?
- Does a delegation remain within the delegator's authority?
- Is this actor allowed to use this channel with this type of data?
- Does the action require a separate approver or verifier?
- Which policy version and controls produced the decision?

The first policy specification does not need to implement every possible
institutional relationship. It does need stable identifiers, explicit
references, deterministic precedence, and validation that rejects broken or
authority-amplifying relationships.

## Decision Lifecycle

The target operating flow is:

1. Authenticate the principal and identify the authorized goal.
2. Attribute the proposed action to an agent, role, and delegation context.
3. Resolve the applicable policy bundle and precedence.
4. Evaluate authority, capability, resource, channel, and control constraints.
5. Return `allow`, `deny`, or `require_approval` with applicable control
   references.
6. Prevent dispatch unless the decision and any required approval authorize
   the exact action.
7. Record the decision, approval, execution result, and policy provenance.
8. Use monitored outcomes and reviewed evidence to improve policy through a
   controlled revision process.

An absent, invalid, stale, or ambiguous decision must not be interpreted as
permission to dispatch.

## Evidence and Improvement Loop

Evidence is part of the control path, not an after-the-fact narrative. A
decision record should connect the proposed action to its actor, authority,
policy version, controls, disposition, approval state, and execution result.

Evidence supports investigation, audit, and assurance work. It does not by
itself prove legal or regulatory compliance. Monitoring should identify
missing evidence, policy conflicts, control failures, overrides, and changing
risk conditions. Material policy changes should have an owner, rationale,
approval, effective date, validation result, and rollback path.

## Current Alpha Versus Target Architecture

| Area | Current alpha | Target architecture |
| --- | --- | --- |
| Policy source | Compatibility XML baseline plus experimental Policy Bundle v0.1 | Stable, versioned governance bundles |
| Validation | XML structure plus v0.1 shape, reference, lifecycle, and delegation checks | Cross-bundle and runtime-context validation |
| Compilation | Plain-text XML rendering plus deterministic v0.1 policy artifacts | Stable artifacts consumed by enforcement integrations |
| Decisions | Documented intended outcomes | `allow`, `deny`, and `require_approval` decision point |
| Enforcement | Not implemented | Pre-dispatch tool and action gating |
| Evidence | Human-readable requirements | Structured, append-only, redacted decision evidence |
| Evaluation | Documentation recall | Behavioral and adversarial governance scenarios |

## Non-Goals

The harness is not intended to replace model safety work, identity systems,
sandboxing, workflow engines, security monitoring, or GRC systems. It aims to
provide portable governance definitions and decision evidence that those
systems can consume or enforce.

The project does not claim certification, legal sufficiency, guaranteed safe
behavior, or compliance with an external framework.

## Conceptual Context

The institutional framing is consistent with broader arguments that alignment
in multi-agent systems depends on the surrounding harness, communication
structure, monitoring, and iterative governance—not only on the properties of
an individual model. For related context, see the Cosmos Institute essay
[Of Swarms and Sand Gods](https://blog.cosmos-institute.org/p/of-swarms-and-sand-gods).
