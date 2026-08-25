# Roadmap

The harness is being developed in small milestones. Each milestone must leave the repository usable and testable.

## 0. Product and Safety Contract

**Status:** implemented in the alpha foundation.

- Define the target user, scope, non-goals, instruction hierarchy, and safety invariants.
- Distinguish implemented capabilities from planned enforcement.
- Mark experimental measurement concepts clearly.

**Exit criteria:** the README and safety model state what the harness does, what it does not do, and how instruction conflicts are resolved.

## 1. Engineering Foundation

**Status:** implemented in the alpha foundation.

- Provide an installable Python package and command-line interface.
- Make examples independent of the current working directory.
- Use interoperable JSONL and deterministic evaluation functions.
- Add automated tests and continuous integration.

**Exit criteria:** a fresh clone installs without runtime dependencies, validates and renders the baseline, and passes its tests.

## 2. Governance Graph and Policy Compiler

**Status:** implemented as an experimental v0.1 foundation.

- Define a versioned governance bundle representing principals, agents, roles,
  capabilities, resources, delegation edges, controls, approvals, and evidence
  requirements.
- Validate referential integrity, scoped delegation, and authority
  non-amplification.
- Add provenance, effective dates, review dates, and policy precedence.
- Compile a policy bundle into prompts and runtime decision data.

**Exit criteria:** missing principals, invalid references, and delegations that
create authority the delegator does not hold fail with precise locations.
Deterministic compilation produces identical artifacts from identical inputs.

The compiler produces policy data, not a runtime authorization decision. The
format may change before the first stable release.

## 3. Enforcement and Evidence

**Status:** the Slice B decision contract, Dogfood 0, and Approval Grant v0.1
are complete. Identity verification, trusted request normalization,
pre-dispatch enforcement, and durable evidence remain planned.

Implemented:

- Evaluate a proposed action and return `allow`, `deny`, or `require_approval`.
- Expose identical decision semantics through the Python SDK and CLI.
- Return stable reasons, effective constraints, policy provenance, and a
  proposal-only evidence record.
- Verify exact-bound approval grants with deterministic, caller-supplied
  identity-boundary, freshness, revocation, and reuse state.
- Return a separate `satisfied` or `not_satisfied` verification result without
  changing Decision Result v0.1 semantics or consuming the grant.
- Retain valid and schema-invalid Action Request objects in local v0.2 shadow
  observations, verify them against the shared evaluator, and report explicit
  pilot metrics.

Remaining:

- Build trusted request-normalization profiles and exercise the first MCP
  reference profile in explicitly non-enforcing shadow mode.
- Extend policy selectors only from observed normalization requirements.
- Expose the shared evaluator through a language-neutral sidecar or service.
- Add a guided initializer, generated scenarios, and explicitly non-enforcing
  shadow mode for progressive adoption.
- Enforce tool, data, delegation, budget, time, and reversibility constraints.
- Produce append-only, redacted decision evidence tied to policy versions.

### Dogfood 0 — repository-development shadow pilot

**Status:** complete through `observation.dogfood.031` with 25 material actions.

Before selecting the next Slice C implementation, the project applied the
current evaluator to real development actions in this repository. The pilot
remained explicitly non-enforcing and preserved existing user, Codex, Git, and
GitHub controls.

The pilot:

- modeled repository-development authority in Policy Bundle v0.1.
- covered deterministic allow, deny, approval, stale, malformed, and unmapped
  scenarios.
- observed 25 real material actions across ten capability categories.
- measured mapping coverage, decision agreement, false allows, false blocks,
  approval load, normalization effort, and evidence completeness.
- used recorded findings to rank normalization, selectors, initialization,
  approval grants, enforcement, and evidence retention.

See the [Repository Development Dogfooding Plan](docs/DOGFOOD_PLAN.md).

**Dogfood exit criteria:** met. Every baseline scenario passes, all 31 observed
decisions reproduce from minimized artifacts, and the completed evidence ranks
the next three product gaps.

### Completed milestone — Approval Grant v0.1

The versioned Approval Grant contract and deterministic, side-effect-free
verifier are implemented before any pre-dispatch adapter. The milestone maps
to `APR-002` through `APR-005` and:

- bind a grant to the exact subject, capability, resource, parameter digest,
  decision, policy, scope, and expiry required by its approval rule;
- verify approver eligibility, quorum, separation of duties, freshness, and
  explicit revocation or reuse state;
- fail closed for missing, stale, mismatched, insufficient, self-approved,
  revoked, or reused grants; and
- expose equivalent SDK and CLI verification results with portable conformance
  fixtures and proposal-only evidence.

This milestone does not collect approvals, dispatch actions, enforce returned
constraints, or provide durable evidence storage.

**Exit criteria:** met. Deterministic conformance cases prove that an exact valid
grant verifies as satisfying a `require_approval` decision and every
mismatched or invalid grant fails closed without changing Decision Result
semantics or dispatching an action.

### Next milestone — MCP request normalization and shadow reference

Build the first versioned integration profile at the MCP boundary while
keeping all authority, policy, decision, approval, and evidence semantics in
the framework-neutral core. This milestone must:

- translate an MCP tool-call proposal and explicitly supplied identity and
  goal context into Action Request v0.1 without discarding security-relevant
  arguments;
- define exact, reviewable mappings from MCP server and tool identifiers to
  policy capability and resource IDs;
- use the shared canonical parameter digest and reject missing, ambiguous,
  unknown, or lossy mappings;
- treat tool annotations and remote content as untrusted data unless an
  explicit trusted adapter boundary supplies the relevant assertion;
- run the shared evaluator and Approval Grant verifier where applicable, with
  portable fixtures proving that MCP does not redefine core semantics; and
- record only proposal-only shadow results, clearly labeled as non-enforcing.

This milestone does not proxy or dispatch MCP calls, authenticate sessions,
collect approvals, atomically consume grants, or claim enforcement. Mapping
findings should determine the smallest selector changes needed before a
trusted pre-dispatch adapter is attempted.

**Exit criteria:** representative MCP call proposals deterministically produce
the expected normalized request, decision, and optional approval-verification
result; incomplete or unsupported calls fail closed; and no path dispatches a
tool or treats MCP metadata as authority.

**Section exit criteria:** denied actions cannot dispatch and every outcome
cites the controls that produced it.

## 4. Behavioral Evaluation

- Add scenario-based tests for prompt injection, confused-deputy behavior, approval bypass, excessive delegation, data leakage, and fail-open behavior.
- Add provider-neutral model adapters and reproducible scoring reports.
- Establish regression thresholds and baseline results.

**Exit criteria:** CI can detect meaningful governance regressions rather than only documentation-recall errors.

## 5. Reference Integrations and Release Governance

- Build one end-to-end tool-using agent example.
- Publish one framework or tool adapter that demonstrates normalization,
  decision enforcement, approval binding, and evidence reporting without
  redefining core semantics.
- Crosswalk controls to established governance and security frameworks without claiming certification.
- Add versioned releases, changelogs, compatibility policy, and maintainer review rules.

**Exit criteria:** the example demonstrates allow, deny, approval, evidence, and policy-update flows from a documented release.
