# MCP Request Normalization and Shadow Reference v0.1

## Status and purpose

MCP Request Normalization and Shadow Reference v0.1 is the first versioned
integration profile for Agent Governance Harness. It converts one caller-
attributed MCP `tools/call` proposal into Action Request v0.1 through an exact,
reviewable mapping, then optionally runs the unchanged Decision Contract v0.1
evaluator and Approval Grant v0.1 verifier.

The reference is deterministic, side-effect-free, and explicitly
non-enforcing. It does **not** connect to an MCP server, proxy or dispatch a
tool call, authenticate a session, verify an identity assertion, collect an
approval, consume a grant, enforce returned constraints, or retain trusted
evidence. Every shadow envelope is marked `mode: "shadow"` and
`proposal_only: true`.

The normative JSON Schemas are:

- [`mcp-call-proposal-v0.1.schema.json`](../schemas/mcp-call-proposal-v0.1.schema.json)
- [`mcp-adapter-mapping-v0.1.schema.json`](../schemas/mcp-adapter-mapping-v0.1.schema.json)
- [`mcp-normalization-result-v0.1.schema.json`](../schemas/mcp-normalization-result-v0.1.schema.json)
- [`mcp-shadow-result-v0.1.schema.json`](../schemas/mcp-shadow-result-v0.1.schema.json)

The portable conformance cases are in
[`mcp-shadow-v0.1.json`](../conformance/mcp-shadow-v0.1.json).

## Normative MCP reference

This profile references the Model Context Protocol revision **2026-07-28**,
specifically its documented
[`tools/call` request](https://modelcontextprotocol.io/specification/2026-07-28/server/tools#calling-tools)
with a tool name and argument object. The profile is not a wire-level MCP
message schema. A caller extracts a proposed tool call and supplies the
governance context that MCP does not establish.

MCP protocol-version claims, server names, titles, descriptions, `_meta`, and
tool annotations are data. They are not identity, authority, mapping keys, or
policy classification. The only server key is the caller-assigned `server_id`
for a configured connection.

## MCP Call Proposal v0.1

Every required field is caller-supplied. Unknown fields are invalid.

| Field | Meaning |
| --- | --- |
| `schema_version` | Exactly `0.1`. |
| `proposal_id` | Stable identifier for this proposed call. |
| `server_id` | Caller-assigned identifier for the configured MCP connection. It is never taken from server metadata. |
| `tool_name` | Exact, case-sensitive MCP tool name used with `server_id` as the mapping key. |
| `arguments` | The proposed JSON object, passed verbatim to the existing canonical parameter digest. |
| `annotations` | Optional untrusted metadata retained only in the proposal artifact. It is never a normalization input. |
| `principal` | The Action Request v0.1 principal and named authentication assertion boundary supplied by the caller. |
| `actor_id` | The caller-attributed actor that proposes or would perform the tool call. |
| `authorized_goal_id` | Caller-supplied stable goal reference. |
| `requested_at` | Caller-supplied UTC time used for lifecycle and decision checks. |
| `requested_constraints` | Optional caller limits. The constraint-source rule below applies. |

Action Request v0.1 distinguishes the authorizing principal from the acting
actor. MCP `tools/call` supplies neither relationship. The proposal therefore
requires `actor_id` separately from `principal.actor_id`; deriving it from a
tool name, server claim, or mapping would invent authority or prevent current
delegation paths from being represented.

The proposal deliberately has no `capability_id`, `resource_id`, `action`,
`channel_id`, `data_classification`, `expected_side_effects`, or `reversible`
field. A caller cannot spoof those policy-facing classifications. They come
only from the matched mapping entry.

## MCP Adapter Mapping v0.1

The mapping artifact contains:

- `schema_version`, exactly `0.1`;
- mapping identity, semantic version, title, provenance, `effective_at`, and
  `review_at`; and
- one or more entries keyed by the exact pair `(server_id, tool_name)`.

Each entry supplies exactly these Action Request classification fields:

- `capability_id`;
- `resource_id`;
- `action`;
- nullable `channel_id`;
- `data_classification`;
- `expected_side_effects`;
- `reversible`; and
- optional default `requested_constraints`.

Entry order is semantically unordered. `expected_side_effects` and the
provenance actor lists are also normalized as unordered collections. Duplicate
exact keys are invalid with `mcp.mapping.ambiguous_key`; an ID or input order
never resolves the ambiguity.

Shape validation requires `review_at` to be later than `effective_at`.
Normalization separately requires the mapping to be effective and not stale
at the proposal's `requested_at`. An exact mapping is classification data, not
authority: the shared evaluator still resolves the capability, resource,
actor, delegation path, controls, and constraints against policy.

## Trust boundaries and field sourcing

The profile has four explicit sourcing rules:

1. `principal`, `actor_id`, `authorized_goal_id`, and `requested_at` come only
   from the caller.
2. `server_id` comes only from the caller's configured-connection identity.
   A server-claimed name or title never substitutes for it.
3. Every policy-facing classification field comes only from the single exact
   mapping entry.
4. `requested_constraints` come from the proposal or the mapping default. If
   both are present they must be exactly equal. If neither is present,
   normalization rejects.

Supplying `principal.authentication.trust_boundary_id` does not authenticate
the assertion. The caller still chooses the trusted identity-boundary set
passed to evaluation. The adapter has no transport or origin-binding field in
v0.1.

## Deterministic normalization

For valid proposal and mapping shapes, normalization:

1. checks mapping lifecycle at `requested_at`;
2. requires one exact `(server_id, tool_name)` match;
3. passes the `arguments` object unchanged to
   `canonical_parameters_digest`;
4. applies the constraint-source rule;
5. copies caller identity, actor, goal, and time fields;
6. copies classification fields only from the matched mapping entry;
7. sorts `expected_side_effects` as the existing Action Request normalizer
   does; and
8. requires the constructed object to pass `validate_action_request`.

Arguments are never coerced. The existing canonical subset permits `null`,
booleans, integers, strings, arrays, and string-keyed objects. Floating-point
values and non-object argument roots fail closed.

### Request ID rule

`request_id` is:

```text
request.mcp.<sha256>
```

The digest input is compact UTF-8 JSON with lexicographically sorted object
keys over the complete proposal content except `annotations`. This includes
the proposal ID, caller-assigned server and tool keys, arguments, principal,
acting actor, goal, time, and any caller constraints. Excluding annotations is
required because untrusted annotations cannot change a constructed field.

The proposal digest in the result covers the complete proposal, including
annotations. As a result, an annotation change remains visible as an input-
integrity change while the constructed Action Request and Decision Result stay
byte-identical.

The mapping digest covers the canonical mapping with entries and declared
unordered collections sorted. Equivalent collection reordering does not
change the digest or any result.

## MCP Normalization Result v0.1

`normalize_mcp_call` and `agent-governance mcp normalize` return one result for
every outcome:

- `normalized`: `action_request` contains the valid Action Request v0.1;
- `invalid_input`: proposal or mapping JSON, shape, version, lifecycle shape,
  unknown-field, or duplicate-key validation failed; or
- `rejected`: the artifacts are valid but cannot safely construct a request.

The result contains a content-derived normalization ID, proposal and mapping
identities and digests, sorted stable reasons, the nullable Action Request, and
`proposal_only: true`. It contains no raw arguments or annotations outside the
original proposal artifact.

## MCP Shadow Result v0.1

The shadow function first uses the same normalizer. Only `normalized` input
reaches the shared evaluator. The envelope contains:

- `outcome`: `evaluated`, `invalid_input`, or `normalization_rejected`;
- mandatory `mode: "shadow"` and `proposal_only: true` markers;
- proposal and mapping identities and digests;
- the normalization outcome and stable reasons;
- the constructed Action Request when normalization succeeded;
- the Decision Result v0.1 exactly as returned by `evaluate_action`;
- an optional Approval Verification Result v0.1 exactly as returned by
  `verify_approval_grant`; and
- minimized proposal-only MCP shadow evidence.

Supplying a grant and verification state does not change the Decision Result.
A satisfied verification remains nested in the envelope while the decision
disposition remains `require_approval`.

The MCP evidence proposal contains only stable IDs, digests, outcome summaries,
and the mandatory non-enforcing markers. It never retains raw arguments or raw
annotations. It is not appended, signed, access-controlled, redacted by a
store, or linked to an execution result.

## Stable reason codes

Errors are sorted by JSON Pointer path, code, and message. These public v0.1
families are stable:

| Code or family | Meaning |
| --- | --- |
| `mcp.proposal.json.*` | Proposal file read or JSON syntax failure. |
| `mcp.proposal.schema.*` | Proposal shape, type, format, range, or unknown-field failure. |
| `mcp.proposal.schema_version.unsupported` | Unsupported proposal contract version. |
| `mcp.proposal.authentication.lifecycle_invalid` | Principal assertion expiry is not later than authentication time. |
| `mcp.mapping.json.*` | Mapping file read or JSON syntax failure. |
| `mcp.mapping.schema.*` | Mapping shape, type, format, range, enum, or unknown-field failure. |
| `mcp.mapping.schema_version.unsupported` | Unsupported mapping contract version. |
| `mcp.mapping.lifecycle_invalid` | Mapping `review_at` is not later than `effective_at`. |
| `mcp.mapping.ambiguous_key` | More than one entry declares or matches the exact key. |
| `mcp.mapping.not_effective` | Mapping is not yet effective at `requested_at`. |
| `mcp.mapping.stale` | Mapping is at or beyond `review_at` at `requested_at`. |
| `mcp.mapping.unknown_server` | No entry uses the caller-assigned `server_id`. |
| `mcp.mapping.unmapped_tool` | The known server has no entry for the exact tool name. |
| `mcp.arguments.uncanonicalizable` | Arguments fall outside the Action Request v0.1 canonical JSON subset. |
| `mcp.context.missing_constraints` | Neither proposal nor mapping supplies required request constraints. |
| `mcp.context.constraints_conflict` | Proposal and mapping constraints are both present but not exactly equal. |
| `mcp.action_request.*` | The constructed request failed the existing Action Request validator. |
| `mcp.policy.*` | A policy file could not be loaded for the shadow command. |
| `mcp.approval.context_incomplete` | Only one of grant and verification state was supplied. |
| `mcp.grant.json.*`, `mcp.state.json.*` | Optional verification file read or JSON syntax failure. |
| `mcp.normalization.succeeded` | A valid Action Request was constructed. |
| `mcp.shadow.evaluated` | The shared evaluator result was embedded without dispatch. |
| `mcp.shadow.approval_verification_embedded` | The shared verifier result was embedded without changing disposition. |

## Python SDK

```python
from agent_governance import (
    evaluate_mcp_shadow,
    load_mcp_adapter_mapping,
    load_mcp_call_proposal,
    load_policy_bundle,
    normalize_mcp_call,
)

mapping = load_mcp_adapter_mapping("governance/mcp-mapping.json")
proposal = load_mcp_call_proposal("governance/mcp-proposal.json")
normalization = normalize_mcp_call(proposal, mapping)

policy = load_policy_bundle("governance/policy.json")
shadow = evaluate_mcp_shadow(
    policy,
    mapping,
    proposal,
    trusted_identity_boundaries={"identity.production"},
)

print(normalization.outcome)
print(shadow.disposition)
print(shadow.to_json())
```

The pure functions do not read the clock, network, filesystem, environment,
MCP transport, identity provider, or approval service and do not mutate input.
The `*_files` helpers perform only the requested JSON reads before calling the
same core.

## CLI

Normalize without policy evaluation:

```bash
agent-governance mcp normalize \
  examples/mcp/mapping.json \
  examples/mcp/proposals/browser-read.json
```

Run non-enforcing shadow evaluation:

```bash
agent-governance mcp shadow \
  examples/policies/multi_agent_operations.json \
  examples/mcp/mapping.json \
  examples/mcp/proposals/browser-read.json \
  --trusted-identity-boundary identity.reference
```

For an exact approval-verification example, add both:

```bash
--grant examples/mcp/approval-grant.json \
--state examples/approval_states/current.json
```

`mcp normalize` exits `0` for `normalized`, `2` for `invalid_input`, and `6`
for a normalization rejection. `mcp shadow` exits `2` for invalid input, `6`
for normalization rejection, and otherwise mirrors the embedded decision:
`0` for `allow`, `3` for `require_approval`, and `4` for `deny`. A satisfied
approval verification never changes the exit code or disposition.

## Conformance and observed gaps

The portable fixture covers allow, deny, require-approval, satisfied approval,
annotation spoofing, unknown server, unmapped tool, ambiguous mapping,
malformed proposal, floating-point arguments, stale mapping, missing context,
and deterministic reordering. Tests prove SDK/CLI parity, unchanged evaluator
and verifier results, proposal-only evidence, and input immutability.

The profile exposes these v0.1 limits without changing core contracts:

- Action Request v0.1 binds all arguments by digest but does not expose
  argument-level selectors. Policy cannot yet distinguish concrete URLs,
  recipients, repository paths, commands, branches, remotes, or other values
  inside one mapped tool's arguments.
- Policy Bundle v0.1 does not declare expected side effects on capabilities,
  so a reviewed mapping must supply them honestly.
- Identity assertion and authorized-goal authenticity remain caller trust
  responsibilities.
- Exact `(server_id, tool_name)` entries cannot safely describe one tool whose
  arguments select materially different capabilities or resources. Such a tool
  needs separate trusted normalization logic or a future selector/request
  contract; v0.1 must reject rather than infer.

These findings inform `DEC-008`, `PTH-001`, and `AUT-002`. This milestone does
not implement selector expansion or trusted identity verification.

## Requirement coverage and boundaries

| Requirements | MCP shadow v0.1 coverage |
| --- | --- |
| `INT-001`, `INT-002`, `INT-003` | MCP details remain in versioned proposal and mapping artifacts; constructed requests, decisions, approvals, and evidence semantics reuse provider-neutral contracts and deterministic JSON. |
| `DX-003` | SDK and CLI call one normalizer, evaluator, and verifier and share conformance fixtures. A decision service remains target work. |
| `DX-005` | Every shadow result is unmistakably non-enforcing and never changes dispatch. |
| `DX-009` | Proposal and mapping versions are explicit; unsupported versions fail closed. |
| `AUT-001` | Caller principal, acting actor, goal, capability, and concrete resource are present in the constructed Action Request. |
| `AUT-002` | A named trust-boundary assertion is consumed, but authentication and origin binding remain unimplemented. |
| `DEC-001`, `DEC-003`, `DEC-005`, `DEC-006` | The unchanged evaluator supplies the three-way result, fail-closed behavior, determinism, and side-effect-free boundary. |
| `APR-002`–`APR-004` | The unchanged exact-bound verifier may be embedded; collection, state sourcing, consumption, and enforcement remain unimplemented. |
| `EVD-001` | Every outcome proposes minimized MCP shadow evidence. Durable retention remains unimplemented. |
| `TST-001` | Unit, CLI/SDK parity, fixture, determinism, failure, and packaging checks cover the new surface. |

`DEC-008` and `PTH-001` are informed by the observed argument-selector gaps;
they are not expanded here. `AUT-002` is informed by the caller/connection
trust boundary but remains target work. `ENF-*` is untouched: no code path
intercepts or dispatches an MCP call.
