# Target Architecture

## Status and Scope

This document describes the architecture the harness is building toward. The
current early alpha parses, validates, and renders an XML governance baseline.
It also validates and deterministically compiles Policy Bundle v0.1. One shared
Python SDK/CLI decision core evaluates Action Request v0.1. The alpha also
provides a shared SDK/CLI Approval Grant v0.1 verifier with explicit
caller-supplied trust, time, revocation, and reuse state. MCP Shadow v0.1 adds
one deterministic request normalizer and explicitly non-enforcing shadow
envelope around those shared contracts. The alpha also includes deterministic
documentation-recall evaluation utilities. It does not authenticate identity,
collect approvals, source or atomically update grant state, gate tool dispatch,
expose a decision service, or persist evidence.

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

## Product Architecture

The target product separates authoring and operations from the runtime action
path while sharing one semantic core.

```text
CONTROL PLANE

wizard / templates -> policy-as-code -> validator / simulator -> policy registry
                                               |
                                               v
                                      immutable policy version

RUNTIME GOVERNANCE PLANE

agent framework -> adapter -> normalized action request -> decision engine
                                                            |
                                    deny <-------------------+
                                                            |
                              approval broker <--- require_approval
                                                            |
                                                            v
                                                  enforcement point
                                                            |
                                                            v
                                                        tool / API
                                                            |
                                                            v
                                                  evidence adapter
```

### Shared semantic core

The policy loader, schema and semantic validator, canonicalizer, authority and
delegation resolver, control resolver, constraint combiner, decision evaluator,
approval verifier, reason codes, and evidence builders form one core library.
The CLI, SDK, sidecar, service, wizard, and adapters call this library or
conform to its versioned protocol and shared fixtures.

No presentation or deployment surface may implement an independent policy
interpretation.

### Control plane

The control plane supports policy initialization, editing, validation,
simulation, review, publication, activation, revocation, rollback, and
inspection. Its durable outputs are reviewable policy files, scenario fixtures,
immutable versions, and provenance—not opaque wizard state.

### Runtime governance plane

The runtime plane normalizes a proposed action, evaluates authority and policy,
verifies any required approval, gates dispatch, and emits linked evidence. The
current core implements the decision and approval-verification steps without
dispatch. Runtime behavior must remain deterministic before execution and
explicit about which execution properties a particular adapter can enforce.

### Adapters

An enforcement adapter has three responsibilities:

1. translate a framework- or tool-specific call into the normalized action
   contract without discarding security-relevant information;
2. prevent dispatch unless a valid decision and approval authorize the exact
   call within returned constraints; and
3. report the execution result and observable side effects for evidence.

Adapters do not grant authority, resolve policy differently, or silently
convert unsupported fields into permissive defaults.

The first reference wedge implements Model Context Protocol (MCP) call
normalization and explicitly non-enforcing shadow evaluation. MCP is an
integration surface, not a source of core policy semantics: server names, tool
names, arguments, annotations, and session identity remain adapter input until
they are mapped to the provider-neutral Action Request contract through an
explicit policy profile. Unmapped or lossy calls fail closed. Tool annotations
are untrusted metadata unless a trusted adapter establishes otherwise. A later
enforcement adapter may mediate MCP dispatch only after request mappings and
constraint expressiveness are demonstrated in shadow mode.

## Deployment Architecture

The same core supports progressive deployment:

- **Embedded SDK:** in-process evaluation for the reference Python path and
  low-friction pilots.
- **Local sidecar or gateway:** a language-neutral boundary near the governed
  application or tool.
- **Shared service:** a multi-application decision point with policy registry,
  availability, authentication, tenancy, caching, and operational controls.

Shadow mode may evaluate and record decisions without blocking existing
dispatch. It must be explicitly labeled as non-enforcing. An organization can
promote scoped capabilities from validation, to shadow observation, to
enforcement without changing the underlying policy semantics.

“Plug and play” ends at the application's real trust boundaries. An
organization must still map identities, capabilities, resources, and approval
owners, and it must place an adapter where the relevant action can be
intercepted. The setup wizard and starter profiles reduce this integration work;
they cannot infer legitimate authority on the organization's behalf.

## Decision Lifecycle

The target operating flow is:

1. Authenticate the principal and identify the authorized goal.
2. Attribute the proposed action to an agent, role, and delegation context.
3. Resolve the applicable policy bundle and precedence.
4. Evaluate authority, capability, resource, channel, and control constraints.
5. Return `allow`, `deny`, or `require_approval` with applicable control
   references.
6. Verify any approval against the exact unresolved decision and current
   caller-supplied state.
7. Prevent dispatch unless the decision and any required approval authorize
   the exact action.
8. Record the decision, approval, execution result, and policy provenance.
9. Use monitored outcomes and reviewed evidence to improve policy through a
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
| Decisions | Side-effect-free Action Request v0.1 evaluator through Python SDK and CLI | The same evaluator exposed through a trusted decision service and adapters |
| Approvals | Exact-bound, side-effect-free grant verifier using explicit caller-supplied state | Trusted collection, authoritative revocation and atomic consumption integrated with enforcement |
| Request normalization | MCP `tools/call` proposals mapped by exact caller-assigned server and tool keys in proposal-only shadow mode | Trusted identity/origin binding and additional provider-neutral profiles derived from observed mapping needs |
| Enforcement | Not implemented | Pre-dispatch tool and action gating |
| Evidence | Proposal-only structured records for decision and approval-verification outcomes | Append-only, redacted decision, approval, and execution evidence |
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
