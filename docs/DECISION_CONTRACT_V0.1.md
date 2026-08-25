# Decision Contract v0.1

## Status and purpose

Decision Contract v0.1 is the experimental Slice B contract for evaluating one
normalized proposed action against one valid Policy Bundle v0.1. The reference
Python evaluator is deterministic and side-effect-free. It returns exactly
`allow`, `deny`, or `require_approval`. The result cites the controlling policy
objects, returns effective constraints, and proposes a structured evidence
record.

The evaluator does **not** authenticate identities, collect or verify approval
grants, dispatch actions, enforce returned constraints, or persist evidence. An
application must not treat the result as proof that execution was mediated. A
separate [Approval Grant v0.1](APPROVAL_GRANT_V0.1.md) verifier checks an exact
grant without changing this contract's three-way disposition. A future trusted
enforcement point must validate the exact request, decision, and any required
approval before dispatch.

The normative JSON Schemas are:

- [`action-request-v0.1.schema.json`](../schemas/action-request-v0.1.schema.json)
- [`decision-result-v0.1.schema.json`](../schemas/decision-result-v0.1.schema.json)
- [`proposed-evidence-record-v0.1.schema.json`](../schemas/proposed-evidence-record-v0.1.schema.json)

## Action Request v0.1

Every field is required unless its value is explicitly nullable. Unknown fields
are invalid so security-relevant input is not silently ignored.

| Field | Meaning |
| --- | --- |
| `schema_version` | Exactly `0.1`. |
| `request_id` | Stable identifier for this proposed action. |
| `principal` | Principal actor plus authentication assertion metadata from a named trust boundary. |
| `authorized_goal_id` | Stable reference to the goal under which the action is proposed. |
| `actor_id` | Actor that proposes or would perform the action. |
| `capability_id` | Policy capability claimed for the action. |
| `action` | Exact normalized action name; it must equal the capability action. |
| `resource_id` | Exact concrete policy resource; it must equal the capability resource. |
| `parameters_digest` | Lowercase `sha256:` digest of canonicalized action parameters. Raw parameters are not required in decision evidence. |
| `requested_at` | Explicit UTC decision time used for lifecycle checks. |
| `context` | Channel, data class, expected side effects, reversibility, and requested execution bounds. |

`principal.authentication` contains `trust_boundary_id`, `assertion_id`,
`authenticated_at`, and `expires_at`. The evaluator accepts the assertion only
when the caller explicitly includes its boundary in
`trusted_identity_boundaries` and the assertion is current at `requested_at`.
This is a trust-boundary contract, not cryptographic identity verification. A
trusted adapter or service remains responsible for verifying the assertion. It
remains responsible for supplying accurate timestamps. Passing an arbitrary
boundary ID does not make a self-assertion trustworthy.

`context.requested_constraints` always declares maximum cost, duration, action
count, and onward delegation depth. A caller that expects no monetary spend
uses an amount of zero. Policy maxima and authority depth can only narrow these
bounds. Data classification and reversibility describe properties of the exact
request and cause `deny` when they conflict with applicable controls.

Policy Bundle v0.1 can authorize a capability whose resource is itself a typed
channel. It cannot yet express a separate channel attached to a non-channel
capability, so the evaluator denies that unsupported combination rather than
ignoring it.

`expected_side_effects` is a closed, normalized request vocabulary retained for
binding and evidence. Policy Bundle v0.1 does not yet declare a machine-readable
side-effect set on each capability, so the evaluator does not infer one from a
free-form description or action name. A trusted normalizer must map the exact
capability honestly; capability-to-side-effect validation remains a future
policy-version requirement.

Parameter bindings use the UTF-8 SHA-256 of compact JSON with lexicographically
sorted object keys, preserved array order, and no escaped non-ASCII characters.
The v0.1 canonical subset permits only `null`, booleans, integers, strings,
arrays, and string-keyed objects; floating-point values are rejected to avoid
cross-runtime numeric ambiguity. The SDK function
`canonical_parameters_digest` returns the required `sha256:<hex>` value.

Examples cover an [allowed browser read](../examples/requests/browser_read_allowed.json),
an [approval-gated email](../examples/requests/email_send_requires_approval.json),
and an [unmapped denied action](../examples/requests/unmapped_action_denied.json).

## Deterministic evaluation

For a valid request and bundle, the evaluator:

1. verifies the named identity boundary is caller-trusted and the assertion is
   current;
2. verifies bundle and applicable-policy lifecycle at `requested_at`;
3. matches the exact capability, action, resource, data class, and channel;
4. derives authority from the principal's roles through a current,
   depth-bounded delegation path to the acting actor;
5. resolves actor- or role-applicable controls at the highest active
   precedence;
6. applies at most one current, scope-matching exception to a control;
7. combines equal-precedence effects using
   `deny > require_approval > allow`;
8. intersects data scopes, takes the narrowest numeric bounds, applies
   reversibility requirements, and includes the remaining delegation bound;
9. returns approval rule details when the result is `require_approval`; and
10. proposes decision evidence for every outcome.

Multiple active exceptions for one control, incompatible cost currencies,
malformed contracts, unsupported versions, missing mappings, stale authority,
and unresolved policy state produce `deny`. Evaluation does not read the clock,
network, filesystem, environment, or approval service and does not mutate its
inputs.

The request digest is the SHA-256 of normalized request JSON. The policy digest
is the existing normalized Policy Bundle source digest. Decision and evidence
IDs are content-derived. Reordering semantically unordered bundle collections
or `expected_side_effects` does not change the result.

For `allow` and `require_approval`, `valid_until` is the earliest expiry among
the identity assertion, bundle, selected policies, authority-path delegations,
and applied exceptions. Denials carry `null` because they confer no permission.
A future enforcement point must still check freshness immediately before
dispatch.

The portable
[`decision-contract-v0.1.json`](../conformance/decision-contract-v0.1.json)
fixture defines common allow, deny, and approval-gated cases. The Python SDK and
CLI parity tests use these semantics; future services and adapters must pass the
same cases rather than implement an independent policy interpretation.

## Decision Result v0.1

The result contains:

- `disposition`: exactly `allow`, `deny`, or `require_approval`;
- `valid_until`: a deterministic upper validity bound for non-deny results;
- stable `reasons`, each with a code, message, and source path when applicable;
- `cited_controls`, including original and exception-adjusted effects;
- normalized `effective_constraints`;
- exact `approval_requirements` for an unresolved approval outcome;
- policy bundle ID, versions, and normalized source digest;
- principal, acting actor, goal, and delegation-path provenance; and
- one embedded `proposed_evidence_record`.

An `allow` result states that the evaluated policy permits only the normalized
action within the returned constraints and supplied trust context. This alpha
has no enforcement adapter, so it cannot ensure that a caller obeys the result.

## Stable reason codes

The v0.1 evaluator emits these public reason-code families:

| Family | Examples | Meaning |
| --- | --- | --- |
| `request.*` | `request.schema.required`, `request.capability_resource_mismatch`, `request.channel_unsupported` | The request is malformed, unsupported, or inconsistent with its named capability. |
| `policy.*` | `policy.schema_version.unsupported`, `policy.stale`, `policy.reference.not_found` | Policy input is invalid or not current. |
| `identity.*` | `identity.boundary_untrusted`, `identity.assertion_expired` | Authentication context is not accepted or current. |
| `authority.*` | `authority.not_granted`, `authority.delegation_inactive` | Roles and current delegation paths do not establish authority. |
| `control.*` | `control.allow`, `control.deny`, `control.require_approval`, `control.restrictive_precedence` | Applicable control resolution and final disposition. |
| `exception.*` | `exception.applied`, `exception.inactive`, `exception.conflict` | Exception applicability changed or could not safely change a control. |
| `constraint.*` | `constraint.data_classification_denied`, `constraint.reversibility_required`, `constraint.cost_currency_conflict` | The exact action conflicts with effective bounds. |

Shape and semantic error suffixes reuse the stable Policy Bundle validation
codes. New codes require a contract-version compatibility review; messages may
be clarified without changing code meaning.

## Proposed Evidence Record v0.1

Every result embeds one proposal-only record. The record links request and
parameter digests, principal assertion metadata, and action identifiers. It
also links policy provenance, decision ID, disposition, reason codes, cited
controls, constraints, approval requirements, and the decision validity bound.
Fields unavailable because input was malformed are `null`, but the denial
itself is still represented.

`proposal_only: true` is a mandatory boundary marker. The evaluator does not
append, sign, retain, redact, or integrity-protect the record in an external
store, and the record contains no execution outcome. Those are later evidence
and enforcement milestones.

## Python SDK

```python
from agent_governance import (
    canonical_parameters_digest,
    evaluate_action,
    load_action_request,
    load_policy_bundle,
)

policy = load_policy_bundle("governance/policy.json")
request = load_action_request("governance/request.json")
# Use this value while constructing the request:
# request["parameters_digest"] = canonical_parameters_digest(parameters)
result = evaluate_action(
    policy,
    request,
    trusted_identity_boundaries={"identity.production"},
)

print(result.disposition)
print(result.to_json())
```

`evaluate_action` performs no I/O. `evaluate_action_files` is a convenience for
loading JSON files and still returns a structured `deny` plus evidence proposal
for read or JSON syntax failures.

## CLI

```bash
agent-governance policy evaluate \
  examples/policies/multi_agent_operations.json \
  examples/requests/browser_read_allowed.json \
  --trusted-identity-boundary identity.reference
```

The CLI writes the same JSON contract as the Python SDK. Exit codes are `0` for
`allow`, `3` for `require_approval`, and `4` for `deny`. Validation and compile
commands retain their existing exit-code behavior.

## Requirement coverage and boundaries

| Requirements | Slice B v0.1 coverage |
| --- | --- |
| `AUT-001`, `AUT-003`, `AUT-006` | Required principal/goal/action identity, role and delegation resolution, and current-policy/current-authority failure behavior are implemented. |
| `AUT-002` | The contract consumes a named, caller-allowed trust boundary and assertion validity; authenticating or cryptographically verifying the assertion remains an integration responsibility. |
| `AUT-004` | Runtime capability, resource, time, and delegation-depth checks are implemented for the fields Policy Bundle v0.1 can express. Delegation-scoped data and budget constraints require a future policy version. |
| `AUT-005` | Principal authority does not transfer transitively without an explicit capability delegation path. Typed message authority remains future work. |
| `DEC-001`–`DEC-007` | Implemented for one Policy Bundle v0.1 and one Action Request v0.1. No dispatch occurs. |
| `DEC-008` | Exact resource/channel, data class, cost, duration, count, reversibility, and delegation bounds are implemented within current v0.1 expressiveness. General selectors and richer channel rules remain future work. |
| `EVD-001` | Every evaluator result proposes structured evidence. Durable or tamper-evident storage is not implemented. |
| `DX-003`, `DX-006` | CLI and Python SDK share the evaluator; input errors include stable codes and JSON Pointer locations. A decision service is not implemented. |

Approval Grant v0.1 is a separate contract layered on unresolved
`require_approval` results. Approval collection, policy registries, action
dispatch, trusted enforcement, execution-result linkage, evidence retention,
shadow mode, and framework or tool adapters remain outside Decision Contract
v0.1.
