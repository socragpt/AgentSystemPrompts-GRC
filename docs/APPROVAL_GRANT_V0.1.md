# Approval Grant v0.1

## Status and purpose

Approval Grant v0.1 is the provider-neutral contract for proving that the
approval requirements in one exact Decision Result v0.1 were satisfied. The
reference Python verifier is deterministic and side-effect-free. It returns
exactly `satisfied` or `not_satisfied` and proposes minimized verification
evidence for every outcome.

The verifier does **not** create or collect approvals, verify cryptographic
identity assertions, query a revocation service, consume a grant, dispatch an
action, enforce decision constraints, or persist evidence. A satisfied
verification does not change the original Decision Result from
`require_approval` to `allow`.

The normative JSON Schemas are:

- [`approval-grant-v0.1.schema.json`](../schemas/approval-grant-v0.1.schema.json)
- [`approval-verification-state-v0.1.schema.json`](../schemas/approval-verification-state-v0.1.schema.json)
- [`approval-verification-result-v0.1.schema.json`](../schemas/approval-verification-result-v0.1.schema.json)

The portable conformance cases are in
[`approval-grant-v0.1.json`](../conformance/approval-grant-v0.1.json).

## Verification boundary

Approval verification consumes five explicit values:

1. one valid Policy Bundle v0.1;
2. one valid Action Request v0.1;
3. the Decision Result v0.1 produced for that request and policy;
4. one Approval Grant v0.1; and
5. caller-supplied Approval Verification State v0.1.

The verifier reevaluates the policy and request with the caller-trusted request
identity boundaries in the supplied state. The supplied decision must equal
that deterministic result and must still have the disposition
`require_approval`. This rejects a stale, malformed, modified, differently
evaluated, `allow`, or `deny` decision before a grant can satisfy it.

The verifier does not read the clock, filesystem, network, identity provider,
approval system, or grant registry. File-loading helpers perform only the
requested JSON reads before calling the same pure verifier.

## Approval Grant v0.1

Every field is required. Unknown fields are invalid.

| Field | Meaning |
| --- | --- |
| `schema_version` | Exactly `0.1`. |
| `grant_id` | Stable caller-assigned identifier used for revocation and single-use state. |
| `approval_requirement_ids` | The complete set of approval rules from the bound decision. |
| `binding` | Exact request, decision, actor, capability, resource, parameter, policy, and scope bindings. |
| `issued_at` | Explicit UTC time at which the approval system issued the grant. |
| `expires_at` | Explicit UTC upper bound, limited by every applicable rule and the decision. |
| `reuse_policy` | Exactly `single_use` in v0.1. |
| `approvals` | Individual approver decisions used to satisfy each rule's eligibility and quorum. |

### Exact binding

The `binding` object contains:

- `request_id` and the normalized `request_sha256`;
- `decision_id` and `decision_disposition`, which is always
  `require_approval`;
- `subject_actor_id`, meaning the acting actor in the request;
- `capability_id` and `resource_id`;
- the request's canonical `parameters_digest`;
- the policy bundle identity, versions, and normalized source digest; and
- `scope`, which exactly equals the Decision Result's effective constraints.

The verifier checks every field independently even though the request and
decision digests also cover them. Explicit bindings make the authority legible
to portable approval and evidence systems. A changed request, parameter,
actor, capability, resource, decision, policy, or scope makes the grant
`not_satisfied`.

Approval Grant v0.1 does not authorize a broader or narrower scope than the
decision. A different scope requires a new action request and decision.

### Individual approvals

Each entry in `approvals` contains:

- the `approval_id` it satisfies;
- the policy actor ID of the approver;
- `approved_at`;
- identity assertion metadata naming a trust boundary, assertion, and
  authentication lifetime; and
- minimized rationale metadata: a controlled `code` and an optional external
  `reference`.

The verifier derives approver roles from the bound policy. Roles stated by an
approval system are not accepted as authority. Each approver counts at most
once toward one requirement. An approval counts only when the actor exists,
holds an eligible role, passes separation of duties, uses a caller-trusted
approver identity boundary, approved while the identity assertion was current,
and approved after the request but no later than grant issuance.

Rationale text is intentionally not part of the core contract. An approval
system may retain additional review material under its own policy. The
proposal-only verification evidence retains rationale codes, not external
references or raw review content.

## Caller-supplied verification state

Approval Verification State v0.1 makes all changing verification inputs
explicit:

| Field | Meaning |
| --- | --- |
| `verified_at` | The UTC time used for freshness checks. |
| `trusted_request_identity_boundaries` | Boundaries the caller has accepted for reevaluating the action request. |
| `trusted_approver_identity_boundaries` | Boundaries the caller has accepted for approver assertions. |
| `revoked_grant_ids` | Grant IDs the caller reports as revoked. |
| `consumed_grant_ids` | Single-use grant IDs the caller reports as already used. |

The two trust-boundary lists are separate because accepting a principal
assertion for action evaluation does not automatically make that system
authoritative for approver identity.

The caller is responsible for constructing this state from trusted systems.
Listing a boundary does not cryptographically verify an assertion. Omitting a
revoked or consumed grant from the supplied lists does not prove that the
grant is live or unused. A future enforcement point must obtain current state
and atomically mark a successfully used grant as consumed.

## Deterministic verification

For valid contract shapes, the verifier:

1. reevaluates the exact request and policy using the supplied request trust
   boundaries;
2. requires exact equality with the supplied Decision Result;
3. requires the reevaluated disposition to remain `require_approval`;
4. compares every grant binding with the request and decision;
5. requires the complete approval-rule set from the decision;
6. checks grant issuance, rule expiry, decision expiry, and caller-supplied
   verification time;
7. rejects caller-reported revocation or prior consumption;
8. derives approver eligibility from policy roles;
9. checks approver identity time, caller-trusted approver boundaries,
   separation of duties, duplicate approvers, and per-rule quorum; and
10. returns a content-derived verification ID and proposal-only evidence.

An expiry equal to `verified_at` or the Decision Result's `valid_until` is no
longer current. Grant expiry may be earlier than a rule permits, but never
later than `issued_at + expires_after_seconds` for any applicable requirement
or later than the decision validity bound.

Identical contract values and state produce identical verification results.
Inputs are not mutated.

## Approval Verification Result v0.1

The result contains:

- `outcome`: exactly `satisfied` or `not_satisfied`;
- a content-derived `verification_id`;
- the grant ID and canonical grant digest;
- the request ID and normalized request digest;
- the supplied decision ID and disposition;
- policy provenance;
- approval-requirement and approver actor IDs;
- the caller-supplied verification time;
- `valid_until` for a satisfied result, otherwise `null`;
- stable reasons; and
- one embedded proposal-only approval-verification evidence record.

`grant_sha256` is the SHA-256 of compact UTF-8 JSON with object keys sorted,
array order preserved, and non-ASCII characters unescaped. Verification and
evidence IDs are derived from their normalized content; they do not use the
clock, randomness, filesystem metadata, or process state.

`satisfied` means only that the supplied grant satisfies the exact unresolved
approval requirements under the supplied verification state. An enforcement
point must still possess the original `require_approval` decision, compare the
exact action at dispatch, enforce its constraints, and safely consume the
single-use grant.

## Stable reason codes

| Family | Examples | Meaning |
| --- | --- | --- |
| `grant.*`, `state.*`, `decision.*` | `grant.schema.required`, `state.schema.unknown_field` | A serialized input is missing, malformed, or unsupported. |
| `approval.*_mismatch` | `approval.parameters_mismatch`, `approval.policy_mismatch`, `approval.scope_mismatch` | The grant does not bind the exact request or decision context. |
| `approval.expiry_*` | `approval.expired`, `approval.expiry_exceeds_rule`, `approval.decision_expired` | The grant or decision is stale or grants an excessive lifetime. |
| `approval.approver_*` | `approval.approver_ineligible`, `approval.approver_untrusted`, `approval.approver_assertion_stale` | An approver cannot count toward quorum. |
| `approval.self_approved` | — | Separation of duties rejects the acting actor's own approval. |
| `approval.insufficient_quorum` | — | Too few distinct eligible approvals satisfy a rule. |
| `approval.revoked`, `approval.reused` | — | Caller-supplied state rejects the grant. |
| `approval.satisfied` | — | Every exact binding and approval requirement passed. |

Shape errors preserve JSON Pointer locations. New reason-code meanings require
a contract-version compatibility review.

## Python SDK

```python
from agent_governance import (
    evaluate_action,
    load_action_request,
    load_approval_grant,
    load_approval_verification_state,
    load_policy_bundle,
    verify_approval_grant,
)

policy = load_policy_bundle("governance/policy.json")
request = load_action_request("governance/request.json")
decision = evaluate_action(
    policy,
    request,
    trusted_identity_boundaries={"identity.production"},
)
grant = load_approval_grant("governance/grant.json")
state = load_approval_verification_state("governance/verification-state.json")

verification = verify_approval_grant(
    policy,
    request,
    decision,
    grant,
    state,
)

print(decision.disposition)  # remains require_approval
print(verification.outcome)  # satisfied or not_satisfied
```

## CLI

After producing the bound Decision Result JSON, verify a grant with explicit
state:

```bash
agent-governance approval verify \
  examples/policies/multi_agent_operations.json \
  examples/requests/email_send_requires_approval.json \
  decision.json \
  examples/approvals/valid.json \
  --state examples/approval_states/current.json
```

The CLI writes the same contract as the Python SDK. It exits `0` for
`satisfied` and `5` for `not_satisfied`. It always writes a verification result
for missing, unreadable, malformed, mismatched, stale, revoked, reused,
ineligible, or insufficient input.

## Examples

The examples cover:

- [`valid.json`](../examples/approvals/valid.json)
- [`stale.json`](../examples/approvals/stale.json)
- [`mismatched.json`](../examples/approvals/mismatched.json)
- [`insufficient-quorum.json`](../examples/approvals/insufficient-quorum.json)
- [`self-approved.json`](../examples/approvals/self-approved.json)
- [`revoked.json`](../examples/approvals/revoked.json)
- [`reused.json`](../examples/approvals/reused.json)

Revocation and reuse examples pair the grant with explicit state under
[`examples/approval_states/`](../examples/approval_states/).

## Requirement coverage and boundaries

| Requirements | Approval Grant v0.1 coverage |
| --- | --- |
| `APR-002` | Exact subject, capability, resource, canonical parameter, request, decision, policy, scope, and expiry bindings are implemented. |
| `APR-003` | Missing, malformed, expired, caller-reported revoked or reused, insufficient, self-approved, untrusted, ineligible, and differently bound grants fail closed. The caller remains responsible for authoritative revocation and reuse state. |
| `APR-004` | Grants are exact-action and single-use. The verifier creates no standing authority and performs no dispatch. |
| `APR-005` | Controlled rationale metadata and minimized proposal-only verification evidence are implemented. Durable, access-controlled, or tamper-evident retention remains a target requirement. |

Approval collection, workflow user interfaces, Slack or webhook delivery,
cryptographic assertion verification, a grant registry, atomic consumption,
pre-dispatch enforcement, execution-result linkage, and durable evidence
retention remain outside Approval Grant v0.1.
