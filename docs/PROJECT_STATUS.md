# Project Status

- **Project:** Agent Governance Harness
- **Status date:** 2026-08-21
- **Lifecycle:** early alpha
- **Repository:** <https://github.com/socragpt/agent-governance-harness>

This is the durable handoff record for maintainers and fresh context windows.
It records verified project state, not aspirations. If it conflicts with the
implementation or tests, verify the code and update this document.

## Executive Summary

Agent Governance Harness is a framework-neutral policy-as-code foundation for
governing tool-using and multi-agent systems. It represents actors, roles,
capabilities, resources, delegations, controls, approvals, exceptions, and
evidence requirements as a versioned governance graph.

The repository validates and deterministically compiles governance policy and
implements the side-effect-free Decision Contract v0.1 evaluator through one
Python SDK/CLI core. It does not authenticate identity, collect or verify
approval grants, block tool dispatch, or persist durable evidence. That
decision-versus-enforcement boundary is central to the project's credibility
and must remain explicit.

## Verified Current State

The alpha foundation implements:

- an installable Python package with no runtime dependencies;
- the `agent-governance` command-line interface;
- a compatibility XML governance prompt parser, validator, and renderer;
- Policy Bundle v0.1 JSON Schema and a multi-agent example;
- semantic validation for identifiers, references, lifecycle dates,
  delegation authority, delegation cycles, approval quorum, and exceptions;
- deterministic compilation to `agent-policy.txt` and `decision-data.json`;
- versioned Action Request, Decision Result, and Proposed Evidence Record v0.1
  JSON Schemas;
- canonical request-parameter bindings over an unambiguous JSON subset;
- a deterministic, side-effect-free evaluator returning exactly `allow`,
  `deny`, or `require_approval` with stable reasons, cited controls, effective
  constraints, authority paths, approval requirements, deterministic validity
  bounds, and policy provenance;
- identical evaluator semantics through the Python SDK and
  `agent-governance policy evaluate` CLI;
- portable allow, deny, and approval-gated conformance fixtures and examples;
- a proposal-only evidence record for validation failures and every decision
  outcome;
- deterministic JSONL documentation-recall evaluations;
- repository-contract, decision, policy, prompt, and evaluation tests; and
- merged-foundation CI and installed-wheel smoke tests across supported Python
  versions, plus a local installed-wheel smoke test for the uncommitted Slice B
  evaluator.

The alpha foundation does **not** implement:

- authenticated identity-to-principal binding;
- cryptographic verification of the identity assertion named by a request;
- approval grant creation, collection, verification, expiry, reuse, or quorum
  workflows;
- pre-dispatch tool or API enforcement;
- a language-neutral decision service or sidecar;
- append-only, integrity-protected decision evidence;
- policy publication, activation, revocation, or rollback;
- provider-neutral agent-framework adapters;
- behavioral or adversarial model evaluation; or
- certification or compliance guarantees.

## Active Change Set

Pull request
[#17](https://github.com/socragpt/agent-governance-harness/pull/17) merged
`agent/repository-clarity` into `main` as `8335966` on 2026-08-21. It delivered:

- product and repository name: **Agent Governance Harness** /
  `agent-governance-harness`;
- Python distribution: `agent-governance-harness`;
- preserved import and CLI: `agent_governance` and `agent-governance`;
- conventional package location: `src/agent_governance/`;
- compatibility XML location: `examples/legacy/SystemPrompt.xml`; and
- standards, templates, research, and glossary content consolidated under
  `docs/`.

There are no open GitHub pull requests. PR #17 and post-merge `main` CI passed
on Python 3.9, 3.11, and 3.13.

The Slice B change set is prepared on `codex/slice-b-decision-contract`, based
on current `origin/main` at `8335966`. It contains the preserved
product-direction and continuity documentation plus the decision-contract
implementation described above. These changes have passed the complete local
verification baseline but have not yet run in GitHub CI.

## Decisions That Should Survive Handoffs

1. **Govern the institution around the model.** The project models delegated
   authority, decision controls, and evidence—not only prompt behavior.
2. **Fail closed.** Missing or invalid authority must not become permission.
3. **Separate compilation, decision, and enforcement.** Compiled artifacts are
   policy data. Decision results do not dispatch actions, and only a future
   trusted enforcement point can ensure the exact call obeys them.
4. **Prevent authority amplification.** An actor cannot delegate capabilities
   or scope it does not hold.
5. **Keep boundaries honest.** Documentation must clearly label implemented,
   experimental, compatibility, research, and planned material.
6. **Favor portable contracts.** Schemas and deterministic artifacts should be
   usable across agent frameworks and model providers.
7. **Preserve compatibility intentionally.** The XML baseline remains shipped
   while the structured Policy Bundle becomes the primary path.
8. **Make product intent enforceable.** Material work must conform to the
   [Product Charter](PRODUCT_CHARTER.md), map to requirements in the
   [Product Specification](PRODUCT_SPEC.md), and pass the charter's anti-drift
   test before acceptance.
9. **One engine, progressive adoption.** The target product exposes one
   governance core through a wizard, CLI, embedded SDK, service, and adapters.
   Organizations should be able to move from policy validation to shadow mode
   and scoped enforcement without rewriting policy or adopting a new agent
   framework.
10. **Make identity trust an explicit evaluator input.** Decision Contract v0.1
    requires a named assertion with a validity window and a caller-configured
    trusted-boundary allowlist. The evaluator does not authenticate or
    cryptographically verify that assertion.
11. **Keep v0.1 selectors exact and conservative.** Capability, action,
    resource, and typed-channel IDs must match exactly; unsupported channel
    composition, overlapping exceptions, and incompatible cost currencies
    fail closed.
12. **Propose evidence without claiming retention.** Every decision returns a
    content-addressed proposal marked `proposal_only`; no append-only or
    tamper-evident store exists yet.

## Recommended Next Milestone

Proceed to the smallest coherent Slice C approval-and-enforcement reference
after the uncommitted Slice B change receives review.

1. Specify Approval Grant v0.1 binding the principal, actor, goal, capability,
   action, resource, canonical parameters, decision, policy digest, scope,
   issue time, expiry, quorum, separation of duties, and reuse policy.
2. Extend the shared evaluator or a separate verifier to reject missing,
   expired, reused, insufficient, self-approved, or differently bound grants
   without changing the three decision outcomes.
3. Add explicitly non-enforcing shadow mode and an evidence sink interface that
   preserves proposal-versus-retained-record distinctions.
4. Build one narrow trusted pre-dispatch adapter only after approval binding is
   tested; keep framework details outside the core evaluator.
5. Demonstrate allow, deny, unresolved approval, approved dispatch, constraint
   enforcement, and execution linkage end to end before adding more adapters or
   an operational UI.

Slice C should not be considered complete until denied, absent, invalid, stale,
or unresolved decisions cannot dispatch through the reference integration.

## Open Design Questions

- How should resource selectors and constraint operators be versioned?
- Which conflicts require `deny` versus `require_approval`?
- How are approval grants bound to a request, policy version, scope, and expiry?
- Which identity assertion format and verifier should first implement the v0.1
  trust-boundary contract without putting vendor semantics in the core?
- What integrity mechanism should protect evidence before an external store is
  selected?
- Which agent framework should be the first reference integration after the
  framework-neutral decision contract is stable?

Resolve these through explicit design notes and tests rather than embedding
unstated assumptions in an integration.

## Verification Baseline

The current expected local check is:

```bash
python -m pip install -e .
python -m compileall -q src examples evals tests
agent-governance validate --strict
agent-governance policy validate examples/policies/multi_agent_operations.json
agent-governance policy evaluate \
  examples/policies/multi_agent_operations.json \
  examples/requests/browser_read_allowed.json \
  --trusted-identity-boundary identity.reference
python evals/run_eval.py
python -m unittest discover -s tests -v
```

The current suite contains 57 tests. On 2026-08-21 the full local checks passed,
including Markdown links, all three decision outcomes, malformed-file denial,
SDK/CLI parity, deterministic conformance fixtures, and an installed-wheel CLI
and SDK smoke test outside the repository. The wheel was built without runtime
dependencies. GitHub CI reflects merged commit `8335966`, not the current
Slice B branch.

## Handoff Checklist

Before ending a material work session:

- record the current branch, PR, and CI outcome;
- move completed work from the active change set into verified current state;
- update decisions and open questions when design choices change;
- reorder the recommended next milestone if priorities change;
- record the commands and results used for verification; and
- keep status claims dated and link to durable code, issues, or pull requests.
