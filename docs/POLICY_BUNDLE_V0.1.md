# Policy Bundle v0.1

## Status and purpose

Policy Bundle v0.1 is an experimental interchange format for expressing an
organization's governance as a multi-actor graph. It is intended to become the
structured source for deterministic, agent-facing instructions and
runtime-ready decision data.

This version is **not an enforcement engine**. Validating or compiling a bundle
does not authorize an action, prevent tool dispatch, verify an identity,
execute an approval, or persist audit evidence. The separate
[Decision Contract v0.1](DECISION_CONTRACT_V0.1.md) can evaluate a normalized
request and propose evidence. The separate
[Approval Grant v0.1](APPROVAL_GRANT_V0.1.md) verifier can determine whether an
exact grant satisfies a `require_approval` result under explicit caller state.
Consumers must still treat compiled output, decisions, and approval
verification as data rather than proof that dispatch was mediated.

The normative JSON Schema is
[`schemas/policy-bundle-v0.1.schema.json`](../schemas/policy-bundle-v0.1.schema.json).
The example in
[`examples/policies/multi_agent_operations.json`](../examples/policies/multi_agent_operations.json)
shows human-to-agent and agent-to-agent delegation, a typed communication
channel, an approval rule, and a time-bounded exception.

## Governance graph

The bundle does not assume one agent or one principal. It defines nodes and
authority relationships that a later decision engine can evaluate:

```text
actor --has--> role --grants--> capability --targets--> resource
actor --delegates capability--> actor
policy --contains--> control --governs--> capability
control --requires--> approval
exception --narrowly replaces--> control effect
```

An `actor` may be a human, agent, or service. A `resource` may be a tool, data
asset, typed communication channel, or service. A capability binds a stable
action name to exactly one resource. Roles establish baseline capability
ownership; delegations make transfers of that authority explicit.

Possessing or receiving a capability makes an actor eligible to propose that
action. It does not itself allow execution. Controls, policy precedence,
exceptions, approvals, constraints, and the bundle's fail-closed default still
apply.

## Top-level contract

Every bundle contains these fields:

| Field | Meaning |
| --- | --- |
| `schema_version` | Exactly `0.1`. |
| `bundle` | Identity, semantic version, owner, lifecycle, default effect, and provenance. |
| `actors` | Human, agent, and service subjects. |
| `roles` | Named capability groupings assigned to actors. |
| `resources` | Tools, data, channels, and services targeted by capabilities. |
| `capabilities` | Stable action/resource pairs. |
| `policies` | Versioned, owned groups of controls with explicit precedence. |
| `approvals` | Quorum, role, separation-of-duties, expiry, and request-binding requirements. |
| `delegations` | Time-bounded capability edges between actors. |
| `exceptions` | Approved, time-bounded, scope-narrowing replacements for a control effect. |

All top-level arrays are required. `approvals`, `delegations`, and `exceptions`
may be empty. Unknown fields are invalid so typos and unsupported semantics do
not silently disappear.

## Required semantics

JSON Schema validates document shape. An implementation must additionally
validate the following graph and lifecycle invariants before compilation:

1. Every ID is unique across the entire bundle, and every reference resolves
   to an object of the expected type.
2. Bundle and policy `review_at` values are later than their `effective_at`
   values. Delegation and exception `valid_until` values are later than
   `valid_from` values. An exception's `approved_at` is not later than its
   `valid_from`.
3. The bundle default is always `deny`. Missing, invalid, stale, conflicting,
   or ambiguous authority must not become `allow`.
4. Delegation edges are acyclic. An actor may delegate only capabilities it
   receives from its roles or from a valid upstream delegation. A downstream
   delegation cannot exceed the upstream `max_depth` or validity window.
5. A control's subject and capability references must resolve. A
   `require_approval` effect must reference an approval rule.
6. An approval quorum cannot exceed the number of actors holding an eligible
   approver role. When `separation_of_duties` is true, the acting actor cannot
   satisfy its own approval.
7. An exception references one control, selects a subset of that control's
   subjects and capabilities, and is fully contained within the policy and
   bundle lifecycle. It may only replace an effect with a less restrictive
   effect. A `require_approval` replacement references an approval rule.
8. The exception's approving actors exist and satisfy the organization's
   out-of-band policy-change authorization. The bundle records this claim but
   v0.1 does not authenticate it.
9. At the highest applicable policy precedence, effects combine according to
   `deny > require_approval > allow`. An ID may stabilize serialization order
   but must never silently resolve a semantic conflict.
10. Constraints only narrow authority. A delegate or exception cannot enlarge
    an upstream cost, duration, action-count, delegation-depth, data-class, or
    reversibility boundary.

Precedence is an integer from 0 through 10000; a larger number has higher
precedence. Policies at the same precedence combine using the restrictive
effect ordering above.

`max_depth` is the number of additional delegation hops permitted after the
recipient. A value of `0` prohibits the recipient from delegating that
capability again.

## Approval binding

An approval rule names eligible roles and a quorum. Its `bind_to` fields define
what must be covered by an eventual approval record:

- `subject` identifies the actor proposing the action;
- `capability` identifies the governed action/resource pair;
- `resource` identifies the concrete target;
- `parameters_digest` binds approval to canonicalized action parameters.

The compiler and decision evaluator preserve these requirements but do not
collect or verify an approval grant. Approval Grant v0.1 supplies a separate,
side-effect-free verifier that rejects missing, expired, caller-reported
revoked or reused, insufficient, self-approved, untrusted, or differently
bound grants. A later trusted enforcement point must source authoritative
state, consume a grant atomically, and repeat the binding checks before
dispatch.

## Deterministic compilation contract

A conforming compiler accepts one valid bundle and produces exactly two
artifacts:

- `agent-policy.txt` contains the bundle identity, fail-closed rule, policy
  precedence, actor and role boundaries, delegation limits, control effects,
  constraints, and approval requirements in stable sections.
- `decision-data.json` contains normalized graph nodes and edges, controls,
  constraints, resolution rules, the canonical source SHA-256, and the
  SHA-256 of `agent-policy.txt`.

Compilation is a pure operation. It must not include the current time, random
values, environment data, network results, absolute paths, or filesystem
metadata. Before rendering, the compiler must:

1. validate schema and semantic invariants;
2. sort entity arrays and graph edges by stable IDs;
3. sort policies by descending precedence and then ID;
4. sort controls, referenced IDs, evidence fields, and approval bindings into
   their documented canonical order; and
5. hash the normalized source rather than its original whitespace.

JSON output uses UTF-8, lexicographically ordered object keys, two-space
indentation, Unix newlines, and exactly one trailing newline. Text output uses
UTF-8, Unix newlines, and exactly one trailing newline. Reordering semantically
unordered input arrays must not change either artifact.

## Validation errors

Errors use JSON Pointer paths and stable codes. Machine-readable output has
this shape:

```json
{
  "valid": false,
  "errors": [
    {
      "code": "reference.not_found",
      "path": "/delegations/0/to_actor_id",
      "message": "Unknown actor id 'agent.beta'",
      "related_path": "/actors"
    }
  ]
}
```

Errors are sorted by `path`, then `code`, then `message`. JSON syntax errors
may additionally include one-based `line` and `column` values. Recommended
stable code families are `json.syntax`, `schema.*`, `id.duplicate`,
`reference.not_found`, `lifecycle.invalid`, `delegation.cycle`,
`delegation.escalation`, `approval.invalid`, `exception.scope`, and
`policy.ambiguous`.

## Command-line surface

The package implements this interface:

```bash
agent-governance policy validate policy.json
agent-governance policy validate policy.json --format json
agent-governance policy compile policy.json --output-dir dist
agent-governance policy evaluate policy.json request.json \
  --trusted-identity-boundary identity.production
```

Validation and compilation return `0` on success and `2` for invalid input.
Evaluation returns `0` for `allow`, `3` for `require_approval`, and `4` for
`deny`, and writes Decision Result v0.1 JSON for every outcome.
Existing XML `validate` and `render` commands remain available during
migration. Compilation writes `agent-policy.txt` and `decision-data.json` to
the requested output directory and never treats those files as an execution
authorization.

## Deliberate v0.1 boundaries

Policy Bundle v0.1 does not define a general condition-expression language,
YAML input, imports, inheritance, cross-bundle precedence, remote policy
resolution, signatures, a registry, an approval service, an evidence store, or
an action dispatcher. It does not migrate or supersede the compatibility
baseline in `examples/legacy/SystemPrompt.xml`.

Those capabilities should be added only after the v0.1 graph, deterministic
compiler, decision contract, and failure behavior are tested. This keeps the
specification small enough to implement with the Python standard library and
stable enough to serve as the foundation for later enforcement.
