# Product Specification

- **Product:** Agent Governance Harness
- **Specification version:** 0.1
- **Status:** target product contract; implementation is partial
- **Last reviewed:** 2026-08-21

This specification translates the [Product Charter](PRODUCT_CHARTER.md) into
testable product requirements. It describes the complete target system unless a
requirement is explicitly marked as implemented. Current behavior is recorded
in [Project Status](PROJECT_STATUS.md).

Normative words such as **must**, **must not**, **should**, and **may** describe
the target product. They do not imply that the alpha already implements the
requirement.

## Product Definition

Agent Governance Harness is a framework-neutral policy decision and evidence
layer for tool-using and multi-agent systems. It consumes authenticated actor
context, a normalized proposed action, applicable policy, and any bound
approval. It produces an explicit governance decision and enables a trusted
enforcement point to gate dispatch. It also records evidence that connects
intent, authority, decision, execution, and policy version.

The core product is the contract and reference implementation for this
governance path—not a general agent runtime.

The phrase “manage agent outcomes” means governing whether agent actions and
their execution paths were authorized, bounded, approved where necessary, and
evidenced. It does not mean optimizing arbitrary business KPIs, judging all
content quality, orchestrating general workflows, or replacing observability
platforms.

## Target Users and Jobs

| User | Job to be done | Required product outcome |
| --- | --- | --- |
| Agent developer | Add consistent governance without rebuilding authorization logic | Stable SDK/CLI contracts, local testability, actionable errors |
| Platform engineer | Govern multiple agents, models, and tools centrally without coupling them to one vendor | Portable policy, decision API, enforcement adapters |
| Policy or risk owner | Translate organizational authority and constraints into reviewable behavior | Human-readable policy, validation, simulation, versioning |
| Approver | Decide an exceptional material action with enough context and bounded scope | Exact request binding, expiry, quorum, separation of duties |
| Operator or incident responder | Understand and contain an unexpected action | Decision trace, policy provenance, execution linkage, revocation |
| Auditor or assurance reviewer | Reproduce why an action was permitted or blocked | Deterministic artifacts and integrity-protected evidence |

## System Context

```text
identity / principal context        policy registry / bundle
              \                         /
               \                       /
                v                     v
agent ------> normalized action request ------> policy decision point
                                                    |
                           deny <-------------------+
                                                    |
                  approval service <--- require_approval
                                                    |
                           allow / approved decision
                                                    |
                                                    v
                                        policy enforcement point
                                                    |
                                                    v
                                               tool / API
                                                    |
                                                    v
                                      evidence and monitoring
```

The identity provider, approval user interface, tool runtime, and external
evidence store may be separate systems. The harness defines what they must
assert, consume, or retain at the governance boundary.

## Product Surfaces

All surfaces must use the same versioned schemas, evaluator, reason codes, and
conformance fixtures.

| Surface | Primary user | Function | Product form |
| --- | --- | --- | --- |
| Setup wizard | Policy owner and developer | Inventory actors, tools, actions, authority, constraints, and approvals; generate a valid starter bundle and tests | Interactive CLI first; optional UI later |
| CLI | Developer and CI | Initialize, validate, compile, simulate, evaluate, test, diff, and inspect policy | Installable command-line package |
| Embedded SDK | Application developer | Normalize requests and evaluate policy in process | Python reference SDK first; additional languages may follow |
| Decision service | Platform team | Offer the same evaluator over a stable local or network contract | Sidecar, container, or deployable service |
| Enforcement adapters | Agent and tool integrator | Intercept framework tool calls, normalize requests, enforce decisions, and report outcomes | Small framework/tool middleware packages |
| Approval connector | Approver and workflow owner | Create and verify exact-bound approval grants | Interface plus reference connector, not a required proprietary workflow system |
| Evidence adapter | Operator and auditor | Persist and retrieve policy-linked decision and execution records | Local reference store plus external sink interface |
| Policy operations | Policy owner | Version, simulate, review, publish, activate, revoke, and roll back policy | Local registry first; service or UI as deployment needs grow |

The wizard improves configuration but is not the source of truth. It generates
the same reviewable policy-as-code and fixtures accepted by the CLI, SDK, and
service.

## Deployment Modes

### Embedded mode

The application imports the SDK and evaluates actions in process. This is the
lowest-friction reference path and the first runtime surface to implement.

### Sidecar or gateway mode

A local process or container provides decisions over a stable protocol. This
supports applications in other languages and keeps policy evaluation separate
from agent runtime code.

### Shared service mode

An organization operates a decision service and policy registry for multiple
applications. This mode adds availability, tenancy, authentication, caching,
and operations requirements but must retain the same core decision semantics.

Organizations may begin in embedded or shadow mode and move to a shared service
without rewriting policy.

## Developer Adoption Journey

The target developer experience is:

1. Install one package or run one container.
2. Run an interactive initializer or choose an organizational starter profile.
3. Answer concrete questions about actors, tools, actions, resources, approvals,
   constraints, and failure behavior.
4. Receive a valid policy bundle, example action requests, and starter tests.
5. Run policy validation and simulation locally.
6. Add one adapter at the agent-to-tool boundary or use a supported framework
   integration.
7. Observe decisions in shadow mode and resolve unmapped or ambiguous actions.
8. Enable enforcement for a scoped capability.
9. Connect approval and evidence interfaces when the governed workflow needs
   them.
10. Promote policy through version-controlled environments and CI.

Proposed future CLI shape, shown only to define the desired experience:

```bash
agent-governance init
agent-governance policy validate governance/policy.json
agent-governance policy simulate governance/policy.json governance/scenarios/
agent-governance run --policy governance/policy.json --mode shadow
agent-governance test governance/
```

Commands that are not documented in the current README must not be presented as
implemented until they exist and are tested.

An integration cannot provide enforcement if it cannot mediate the governed
action. In that case the harness may provide policy validation, simulation, or
advisory decisions, but the product must label the boundary honestly.

## Core Domain Objects

The product must define versioned, serializable contracts for:

- **Policy bundle:** governance entities, relationships, lifecycle, precedence,
  provenance, and default effect.
- **Principal context:** authenticated identity, organization or policy domain,
  active role or delegation context, and authorized goal reference.
- **Action request:** acting actor, capability, concrete resource, parameters or
  parameter digest, channel, data classification, expected side effects,
  reversibility, budget, and request time.
- **Decision result:** `allow`, `deny`, or `require_approval`; matched policy and
  controls; reasons; effective constraints; approval requirements; expiry; and
  integrity/provenance fields.
- **Approval grant:** approver identity, rule, request binding, scope, quorum,
  decision, issue and expiry times, and reuse policy.
- **Execution result:** enforcement-point identity, tool outcome, side effects,
  resource consumption, timestamps, and error state.
- **Evidence record:** stable links among request, policy, decision, approval,
  execution, and redaction/integrity metadata.

Contracts must use stable identifiers and explicit versions. Raw chain of
thought is not a required governance artifact.

## Required Workflows

### 1. Author, validate, and publish policy

1. A policy owner creates or updates a governance bundle.
2. Schema and semantic validation reject broken references, invalid lifecycle,
   ambiguous precedence, authority amplification, and unsupported semantics.
3. Simulation shows expected decisions for representative requests.
4. An authorized review process approves the policy version.
5. The registry makes the immutable version addressable by ID and digest.
6. Activation and rollback are recorded as governed events.

### 2. Evaluate a proposed action

1. An agent or service submits a normalized request and principal context.
2. The decision point resolves the exact policy version and validates all
   inputs.
3. It computes effective authority through roles and valid delegation paths.
4. It resolves applicable controls, precedence, constraints, exceptions, and
   approval requirements.
5. It returns one explicit outcome with cited controls and a proposed evidence
   record.
6. Any missing, stale, unverifiable, conflicting, or unsupported input fails
   closed.

### 3. Obtain and apply approval

1. A `require_approval` decision creates an approval request bound to the exact
   proposed action and decision context.
2. Eligible approvers receive the minimum context needed to decide.
3. The service enforces quorum, separation of duties, expiry, scope, and reuse
   rules.
4. The action is reevaluated or the grant is verified immediately before
   dispatch.
5. A changed actor, capability, resource, parameter digest, policy version, or
   expired grant cannot reuse the approval.

### 4. Enforce, execute, and record evidence

1. A policy enforcement point receives the decision and exact action.
2. It validates integrity, binding, freshness, and effective constraints.
3. It dispatches only a valid `allow` or validly approved action.
4. It measures bounded execution and stops or contains limit violations where
   the integration supports it.
5. It links the execution result and observed side effects to the evidence
   record.

### 5. Monitor and improve governance

1. Monitoring identifies denied actions, approval volume, missing evidence,
   overrides, repeated conflicts, enforcement failures, and changed risk.
2. Reviewers distinguish policy defects, integration defects, malicious
   behavior, and legitimate unmet needs.
3. Changes follow the authoring workflow with tests, review, versioning, and a
   rollback path.
4. Prior decisions remain reproducible against their original policy version.

## Functional Requirements

### Policy and governance graph

| ID | Requirement | Delivery |
| --- | --- | --- |
| POL-001 | The product must represent human, agent, and service actors; roles; capabilities; resources; channels; policies; controls; approvals; delegations; exceptions; and evidence requirements with stable IDs. | Alpha foundation |
| POL-002 | Policy shape and graph semantics must be validated before compilation or decision use. Unknown semantics must not be silently ignored. | Alpha foundation |
| POL-003 | Policy lifecycle, ownership, provenance, precedence, default effect, version, and digest must be explicit. | Alpha foundation |
| POL-004 | Compilation must be deterministic and independent of unordered input representation, current time, absolute paths, and environment state. | Alpha foundation |
| POL-005 | Published policy versions must be immutable and activation or rollback must create a durable event. | Target |
| POL-006 | Cross-bundle composition must define explicit domain, precedence, compatibility, and conflict behavior before it is supported. | Target |

### Identity, authority, and delegation

| ID | Requirement | Delivery |
| --- | --- | --- |
| AUT-001 | Every request must identify an authenticated principal, acting actor, authorized goal, capability, and concrete resource. | Slice B contract |
| AUT-002 | Authentication evidence must be consumed from an explicit trust boundary; the harness must not treat self-asserted actor fields as authenticated. | Target |
| AUT-003 | Eligibility must be derived from current role assignments and valid delegation paths. Possessing a tool or credential is insufficient. | Slice B |
| AUT-004 | Delegation must be acyclic, time-bounded, depth-bounded, and unable to expand capability, resource, data, budget, duration, reversibility, or channel scope. | Validation foundation; Slice B runtime subset |
| AUT-005 | Trust in an actor or message for one purpose must not transitively grant instructional or delegation authority. | Target |
| AUT-006 | Revoked, expired, stale, or unverifiable authority must fail closed. | Slice B except registry revocation |

### Decision point

| ID | Requirement | Delivery |
| --- | --- | --- |
| DEC-001 | The decision point must accept a versioned, normalized action request and return exactly `allow`, `deny`, or `require_approval`. | Slice B |
| DEC-002 | Every result must identify the policy bundle, version or digest, applicable controls, reasons, and effective constraints. | Slice B |
| DEC-003 | Missing, invalid, ambiguous, conflicting, or unsupported inputs must never produce `allow`. | Slice B |
| DEC-004 | At equal applicable precedence, effects must combine using `deny > require_approval > allow`. | Slice B |
| DEC-005 | Equivalent normalized input and policy must produce an equivalent decision and evidence proposal. | Slice B |
| DEC-006 | The evaluator must be side-effect-free and must not dispatch tools, collect approvals, or mutate policy. | Slice B |
| DEC-007 | Constraints must only narrow authority and must be returned in an enforceable normalized form. | Slice B |
| DEC-008 | Policy must be able to govern permitted resources, channels, data classes, budgets, action counts, time bounds, reversibility, and delegation depth without depending on free-form model interpretation. | Slice B subset; richer selectors target |

### Communication and execution path

| ID | Requirement | Delivery |
| --- | --- | --- |
| PTH-001 | Policy must be able to distinguish the requested outcome from the resources, channels, and techniques permitted to obtain it. | Target |
| PTH-002 | Agent-to-agent and external messages must be attributable, typed, scope-bounded, and treated as data unless granted explicit authority. | Target |
| PTH-003 | Integrations should support bandwidth, destination, data-class, rate, and direction constraints where the underlying channel permits them. | Target |
| PTH-004 | Material workflows must support independent verifier or monitor roles that do not inherit the actor's execution authority. | Target |
| PTH-005 | The product must not require disclosure or storage of hidden chain of thought to establish path compliance. | Target |

### Approvals

| ID | Requirement | Delivery |
| --- | --- | --- |
| APR-001 | Approval rules must define eligible roles, quorum, separation of duties, expiry, scope, and required request bindings. | Alpha policy foundation |
| APR-002 | A grant must bind to the subject, capability, resource, canonical parameter digest, policy decision, and expiry required by its rule. | Target |
| APR-003 | Missing, expired, revoked, reused, insufficient, self-approved, or differently bound grants must fail closed. | Target |
| APR-004 | Approval must authorize only the exact requested exception; it must not create standing ambient authority unless policy explicitly defines it. | Target |
| APR-005 | Approval decisions and rationale metadata must be retained as governed evidence with data minimization. | Target |

### Enforcement

| ID | Requirement | Delivery |
| --- | --- | --- |
| ENF-001 | A trusted policy enforcement point must mediate the governed capability before side effects occur. | Target |
| ENF-002 | The enforcement point must validate decision integrity, request binding, freshness, policy version, and approval state before dispatch. | Target |
| ENF-003 | `deny`, unresolved `require_approval`, absent decision, invalid decision, and enforcement-service failure must not dispatch. | Target |
| ENF-004 | Adapters must not reinterpret core decision semantics or weaken effective constraints. | Target |
| ENF-005 | At least one reference integration must demonstrate allow, deny, approval, bounded execution, and evidence flows end to end. | Target |

### Evidence and monitoring

| ID | Requirement | Delivery |
| --- | --- | --- |
| EVD-001 | Every decision outcome, including validation failure and denial, must create or propose a structured evidence record. | Slice B proposal |
| EVD-002 | Evidence must link request, actor and authority context, policy, controls, decision, approval, enforcement point, execution, and outcome using stable identifiers and digests. | Target |
| EVD-003 | Retained evidence must be append-only or tamper-evident, access-controlled, and redacted according to explicit policy. | Target |
| EVD-004 | Evidence must be sufficient to reproduce the governance decision without requiring secrets, unnecessary personal data, or model chain of thought. | Target |
| MON-001 | Monitoring must detect missing evidence, policy conflicts, invalid approvals, enforcement bypass, repeated overrides, and integrity failure. | Target |
| MON-002 | Material policy changes must record owner, rationale, review, effective time, validation, compatibility, and rollback information. | Target |

### Evaluation and portability

| ID | Requirement | Delivery |
| --- | --- | --- |
| TST-001 | CI must test policy shape, graph semantics, determinism, failure behavior, package installation, and stable CLI or API contracts. | Alpha foundation |
| TST-002 | Behavioral scenarios must cover prompt injection, confused-deputy behavior, authority amplification, approval bypass, stale policy, data leakage, resource exhaustion, path violation, collusion pressure, and fail-open behavior. | Target |
| TST-003 | Regression thresholds and fixtures must make governance behavior changes visible before release. | Target |
| INT-001 | Core policy, request, decision, approval, and evidence contracts must remain provider- and framework-neutral. | Target |
| INT-002 | Vendor-specific identity, tool, workflow, and evidence details must remain in versioned adapters. | Target |
| INT-003 | Reference artifacts must use open, documented serialization formats and deterministic canonicalization. | Alpha foundation |

### Adoption and developer experience

| ID | Requirement | Delivery |
| --- | --- | --- |
| DX-001 | An interactive and non-interactive initializer must generate a valid starter policy, representative requests, and starter tests from explicit organizational inputs. | Target |
| DX-002 | Starter profiles and control packs must remain editable policy-as-code and must not claim universal applicability or certification. | Target |
| DX-003 | The embedded SDK, CLI evaluator, and decision service must return equivalent outcomes and reason codes for equivalent normalized inputs. | SDK/CLI in Slice B; service target |
| DX-004 | A supported adapter must intercept a framework or tool call, normalize it, enforce the decision, and report the result without requiring an application rewrite. | Target |
| DX-005 | Shadow mode must produce decisions and evidence without changing whether the existing application dispatches, and must be unmistakably labeled non-enforcing. | Target |
| DX-006 | Validation and simulation errors must identify the exact policy or request location, stable reason code, and actionable remediation. | Alpha foundation onward |
| DX-007 | Generated configurations must include deny, approval, stale-input, and unmapped-action scenarios rather than only successful examples. | Target |
| DX-008 | An organization must be able to move from embedded to service deployment without changing core policy semantics. | Target |
| DX-009 | Adapters and control packs must declare supported contract versions and fail closed on incompatible versions. | Target |
| DX-010 | A clean reference quickstart must demonstrate first policy validation in minutes and a governed tool call in one focused integration session. | Target; benchmark before release |

## Non-Functional Requirements

- **Safety:** fail closed at every trust boundary; never convert service
  unavailability or parsing failure into permission.
- **Determinism:** the decision path must be reproducible from normalized input
  and immutable policy.
- **Explainability:** every decision must identify governing controls and
  machine-readable reasons without relying on hidden reasoning.
- **Integrity:** requests, decisions, approvals, policies, and evidence must
  support binding through canonical digests or stronger attestations.
- **Data minimization:** contracts and evidence must avoid collecting data not
  required for governance, investigation, or an explicitly configured duty.
- **Performance:** the product should support pre-dispatch evaluation without
  forcing applications to bypass governance for normal operations. Performance
  targets must be measured per integration and may not weaken fail-closed
  behavior.
- **Availability:** deployments must define whether outage produces `deny` or a
  narrowly governed emergency approval path. Silent fail-open is prohibited.
- **Portability:** a policy and normalized request should retain core semantics
  across supported model and agent frameworks.
- **Compatibility:** public schemas, decision reason codes, and evidence fields
  require versioning and documented migration.
- **Testability:** each normative requirement must be demonstrable through unit,
  contract, scenario, integration, or adversarial tests.

## Reference Acceptance Scenarios

The complete reference implementation must demonstrate at least:

1. **Allowed bounded action:** a delegated agent uses an authorized capability
   on an in-scope resource within time, cost, data, and channel constraints.
2. **Denied authority amplification:** an agent attempts to delegate or exercise
   a capability outside its authority.
3. **Approval-gated action:** a material action is held until an eligible,
   independent quorum approves the exact request.
4. **Stale approval rejection:** an expired, reused, or parameter-mismatched
   grant cannot authorize dispatch.
5. **Confused deputy:** an authenticated but unauthorized requester attempts to
   induce a more privileged agent to act.
6. **Prompt-injected path violation:** untrusted content asks the agent to use an
   unauthorized tool, destination, or communication channel.
7. **Policy conflict:** equally applicable controls disagree and resolve to the
   most restrictive effect with explicit reasons.
8. **Dependency failure:** missing identity, policy, decision service, or
   evidence sink results in documented fail-closed behavior.
9. **Bounded exception:** a valid, time-limited exception narrows subjects and
   capabilities and expires without leaving residual authority.
10. **Reproducible audit:** a reviewer reconstructs a historical decision from
    immutable policy and evidence without relying on the original chat.
11. **Cross-agent channel control:** one agent attempts to send disallowed data
    or instructions through an unapproved channel.
12. **Enforcement integrity:** a modified decision or action request fails its
    binding check and cannot dispatch.

## Delivery Slices

### Slice A — Policy definition and compilation

Versioned governance graph, semantic validation, deterministic compilation,
CLI, examples, packaging, and tests. This is the current alpha foundation.

### Slice B — Decision contract

Versioned action request, deterministic evaluator, three explicit outcomes,
matched controls, effective constraints, stable reason codes, and proposed
evidence record exposed through the Python SDK and CLI. This milestone is
implemented in the current alpha.

### Slice C — Approval and enforcement reference

Interactive initialization, shadow mode, exact-bound approval grants, one
trusted pre-dispatch adapter, denial and approval blocking, execution linkage,
and failure-mode tests.

### Slice D — Evidence and controlled operations

Tamper-evident retention interface, policy registry and lifecycle, monitoring,
revocation, rollback, redaction, and operational metrics.

### Slice E — Portability and assurance

Additional adapters, adversarial evaluation, cross-domain policy contracts,
compatibility policy, releases, and conceptual framework mappings without
certification claims.

Each slice must leave the repository installable, testable, and honest about
what remains outside the enforcement boundary.

## Definition of a Complete Reference Product

The initial reference product is complete when:

- all target contracts above are versioned and documented;
- policy authoring, validation, simulation, publication, decision, approval,
  enforcement, evidence, monitoring, and rollback are demonstrated end to end;
- the acceptance scenarios pass automatically where deterministic and have
  reproducible procedures where human judgment is required;
- denied, unresolved, malformed, stale, or integrity-invalid actions cannot
  dispatch through the reference integration;
- every outcome cites policy and controls and produces sufficient evidence for
  reproduction;
- a model or agent framework can be replaced without changing core policy
  semantics;
- a new adopter can generate a reviewable starter policy, simulate scenarios,
  integrate one supported governed tool, observe shadow decisions, and enable
  scoped enforcement using documented workflows rather than bespoke engine
  code;
- the CLI, embedded SDK, decision service, and reference adapter pass shared
  conformance fixtures;
- security, compatibility, operations, and contribution guidance support an
  external adopter; and
- documentation contains no claims of capabilities that the reference system
  does not enforce.

This definition does not mean the product has solved general AI alignment or
all forms of collusion, deception, policy error, or institutional failure. It
means the repository contains a credible, bounded, testable governance harness
that demonstrates its chartered workflows.

## Product Decision Gate

Before accepting a new feature, map it to one or more requirement IDs and run
the [Charter anti-drift test](PRODUCT_CHARTER.md#anti-drift-test). Features with
no requirement mapping require a product-spec amendment or should live outside
this repository.
