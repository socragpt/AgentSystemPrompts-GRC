# Project Status

- **Project:** Agent Governance Harness
- **Status date:** 2026-08-22
- **Lifecycle:** early alpha
- **Repository:** <https://github.com/socragpt/agent-governance-harness>
- **Verified `main`:** `79b7b4a9d3add6805339bf021256f49375515e24`

This document records verified project state, current decisions, active work,
and the next recommended action. Implementation and tests are authoritative if
they disagree with this document.

## Executive Summary

Agent Governance Harness is a framework-neutral policy-as-code foundation for
governing tool-using and multi-agent systems. The current alpha validates and
deterministically compiles governance policy. It also evaluates normalized
action requests through one side-effect-free Python SDK and CLI core.

The evaluator returns exactly `allow`, `deny`, or `require_approval`, with
stable reasons, effective constraints, authority paths, policy provenance, and
proposal-only evidence. It does not authenticate identity, verify approval
grants, block tool dispatch, enforce execution constraints, or persist durable
evidence.

The active milestone is a non-enforcing repository-development dogfood pilot.
Phase 1 is implemented and locally verified on `codex/dogfood-phase-1`. It has
not been merged. The maintainer explicitly authorized live shadow observation
and publication of the Phase 1 candidate for review on 2026-08-22. The pilot is
now running. Pull-request publication does not authorize merge.

## Verified Current State

The alpha foundation implements:

- an installable Python package with no runtime dependencies.
- the `agent-governance` command-line interface.
- a compatibility XML governance prompt parser, validator, and renderer.
- Policy Bundle v0.1 JSON Schema and a multi-agent example.
- semantic validation for identifiers, references, lifecycle dates,
  delegation authority, delegation cycles, approval quorum, and exceptions.
- deterministic compilation to `agent-policy.txt` and `decision-data.json`.
- Action Request, Decision Result, and Proposed Evidence Record v0.1 JSON
  Schemas.
- canonical request-parameter bindings over an unambiguous JSON subset.
- a deterministic, side-effect-free evaluator with exact policy, authority,
  constraint, and lifecycle checks.
- identical evaluator semantics through the Python SDK and CLI.
- portable allow, deny, and approval-gated conformance fixtures.
- a proposal-only evidence record for validation failures and every decision
  outcome.
- deterministic JSONL documentation-recall evaluation utilities.
- repository-contract, decision, policy, prompt, and evaluation tests.
- a human-first documentation path for users, policy authors, integrators,
  contributors, maintainers, and coding agents.

The alpha foundation does **not** implement:

- authenticated identity-to-principal binding.
- cryptographic verification of identity assertions.
- approval grant creation, collection, verification, expiry, revocation,
  reuse, or quorum workflows.
- pre-dispatch tool or API enforcement.
- a language-neutral decision service or sidecar.
- append-only, integrity-protected decision evidence.
- policy publication, activation, revocation, or rollback.
- provider-neutral agent-framework adapters.
- behavioral or adversarial model evaluation.
- certification or compliance guarantees.

The local `codex/dogfood-phase-1` branch adds a Phase 1 candidate with:

- an exact-resource repository-development Policy Bundle v0.1;
- 14 deterministic allow, deny, approval, stale, malformed, and unmapped
  Action Request fixtures;
- expected dispositions, reason codes, cited controls, and approval
  requirements for each fixture;
- a closed observation schema that retains artifact references and digests;
- a dependency-free local recorder for canonical request, policy, decision,
  and proposal-only evidence artifacts;
- a manual shadow procedure with an explicit live-observation gate; and
- 12 dogfood tests for policy validity, decisions, SDK/CLI parity,
  determinism, fail-closed behavior, observation validation, recording, and
  reproduction.

These files do not change evaluator semantics. They do not authenticate,
approve, dispatch, enforce, or create trusted evidence.

## Recently Delivered

Pull request
[#18](https://github.com/socragpt/agent-governance-harness/pull/18) merged the
Slice B decision contract into `main` as `5699933` on 2026-08-21. It delivered
the normalized request, evaluator, three decision outcomes, stable reasons,
constraints, policy provenance, and proposal-only evidence described above.

Pull request
[#20](https://github.com/socragpt/agent-governance-harness/pull/20) merged the
human-first repository cleanup into `main` as `baf580d6` on 2026-08-21. It
delivered:

- a shorter public quickstart and explicit current capability boundary.
- separate documentation paths for policy authors, SDK integrators,
  contributors, and maintainers.
- clear secondary status for compatibility, reference, template, research,
  and documentation-recall material.
- task-routed coding-agent guidance instead of a read-everything startup path.

The change did not alter schemas, evaluator semantics, reason codes, CLI
compatibility, or runtime behavior. Post-merge
[`main` CI run 32540910938](https://github.com/socragpt/agent-governance-harness/actions/runs/32540910938)
passed on Python 3.9, 3.11, and 3.13, including wheel builds and installed-wheel
smoke tests.

Pull request
[#21](https://github.com/socragpt/agent-governance-harness/pull/21) merged the
Dogfood 0 plan into `main` as `79b7b4a9` on 2026-08-22 UTC. It added the pilot
plan and aligned the roadmap, business purpose, documentation guide, and
project status. It did not add pilot runtime artifacts or change evaluator
semantics. Post-merge
[`main` CI run 32541704684](https://github.com/socragpt/agent-governance-harness/actions/runs/32541704684)
passed on Python 3.9, 3.11, and 3.13.

## Active Milestone: Dogfood 0

The [Repository Development Dogfooding Plan](DOGFOOD_PLAN.md) governs the
active milestone. Phase 1 builds the policy, fixtures, expected results,
observation contract, recorder, procedure, and tests. The local Phase 1
candidate meets its acceptance criteria.

Dogfood 0 is explicitly shadow and non-enforcing. User, Codex, operating-system,
Git, and GitHub controls remain authoritative. The pilot will not treat
evaluator output as permission to execute.

The complete pilot will:

1. model repository-development actors, capabilities, resources, controls, and
   approval expectations in Policy Bundle v0.1;
2. create deterministic allow, deny, approval, stale, malformed, and unmapped
   scenarios;
3. observe at least 25 real material development actions across at least six
   capability categories;
4. record minimized decisions, expected outcomes, disagreements, and workflow
   friction; and
5. use the evidence to rank the next three product gaps.

The pilot tests adoption assumptions for `DX-005`, `DX-007`, and `DX-010`. It
does not claim those target requirements are implemented.

No live development observations were collected during Phase 1. The maintainer
opened the live gate after reviewing the verified Phase 1 result. The first
observed material action records that authorization in this status document.
Harness results remain advisory and do not authorize execution.

The Phase 1 anti-drift review passed. The work serves the named repository
workflow, reuses the shared policy and decision semantics, preserves
fail-closed behavior, keeps trust assumptions explicit, remains
framework-neutral, and produces reproducible artifacts. The documentation does
not describe shadow decisions as enforcement or verified approval.

## Decisions That Should Survive Handoffs

1. **Govern the institution around the model.** The project models delegated
   authority, decision controls, and evidence—not only prompt behavior.
2. **Fail closed.** Missing or invalid authority must not become permission.
3. **Separate compilation, decision, and enforcement.** Policy artifacts and
   decision results do not dispatch actions.
4. **Prevent authority amplification.** An actor cannot delegate authority it
   does not hold.
5. **Keep boundaries honest.** Documentation must distinguish implemented,
   experimental, compatibility, research, and planned material.
6. **Favor portable contracts.** Core schemas and semantics must remain
   independent of model, framework, workflow, and tool vendors.
7. **Preserve compatibility intentionally.** The XML baseline remains shipped
   while Policy Bundle v0.1 is the structured path forward.
8. **Use one semantic core.** The CLI, SDK, future service, and adapters must
   share conformance fixtures and reason codes.
9. **Make identity trust explicit.** The current evaluator consumes a named,
   caller-allowed trust boundary but does not verify it cryptographically.
10. **Keep v0.1 selectors exact and conservative.** Unsupported composition,
    ambiguity, and incompatible constraints fail closed.
11. **Propose evidence without claiming retention.** Every result contains a
    record marked `proposal_only`; no trusted evidence store exists.
12. **Dogfood before selecting the next build.** Pilot evidence should decide
    whether normalization, selectors, initialization, approvals, enforcement,
    or evidence retention is the highest-priority gap.
13. **Shadow is not enforcement.** A dogfood decision must not replace existing
    authority, approval, or tool controls.
14. **Use conservative pilot dispositions.** Pull-request merges require
    approval. Force-push, remote deletion, and release creation are denied.
15. **Keep review authority read-only.** The reviewer receives repository-read
    and local-validation delegations, not edit or publication authority.
16. **Do not reduce governance to a compliance boolean.** Retain the three-way
    disposition, observed out-of-band approval state, action occurrence, and
    agreement classification separately.
17. **Retain minimized artifacts.** Observations link canonical request,
    policy, decision, and proposal-only evidence files by reference and digest.
    They do not retain raw parameters, prompts, secrets, or chain of thought.

## Open Design Questions and Findings

- Policy Bundle v0.1 cannot model repository path, command, branch, or remote
  selectors. Dogfood 0 uses exact resource classes and records ambiguous or
  overbroad normalization as a finding.
- What trusted component should normalize concrete development actions to
  exact v0.1 capability and resource IDs?
- The Phase 1 observation contract can reproduce a decision from minimized,
  digest-linked artifacts. Live use must test whether its controlled fields
  are operationally sufficient.
- The observation contract records whether an out-of-band approval was
  requested and received. It does not claim that the harness verified an
  Approval Grant.
- Policy Bundle v0.1 does not bind a resource class to concrete path, command,
  branch, or remote parameters. The pilot normalizer must preserve that limit.
- Action Request v0.1 retains expected side effects, but Policy Bundle v0.1
  does not declare a comparable capability-side-effect contract.
- The named identity boundary and authorized goal remain procedural inputs.
  The current evaluator does not verify either claim.
- The first live review found that the observation record does not explicitly
  identify material actions or record whether a decision was useful. Current
  progress counts infer materiality from the capability, and usefulness
  remains unmeasured.
- The pilot has no built-in aggregate report. Current metrics require a
  separate query over the local JSONL index.
- A malformed live request failed closed because `write` is not a supported
  side-effect value. The recorder rejects invalid requests, so it cannot retain
  that denial through its normal path. This limits live evidence for malformed
  and request-construction failures.
- The recorder accepts an operator-supplied observation timestamp but does not
  validate it against the request or recording time. One sampled read exposed
  this risk when its supplied timestamp was later than the recorder invocation.
- Which pilot finding should take priority if normalization, approval, and
  evidence gaps appear together?
- After the pilot, how should resource selectors and constraint operators be
  versioned?
- Which identity assertion verifier and enforcement adapter should become the
  first trusted references?

Resolve these questions through explicit fixtures, observations, design notes,
and tests. Do not embed unstated assumptions in an adapter.

## Next Recommended Action

Continue the authorized live shadow pilot. Publish and review the Phase 1
candidate through the normal pull-request workflow. Merge still requires
separate authorization.

The live pilot must observe at least 25 material actions across at least six
capability categories. Use those observations to rank the next three product
gaps. Do not implement approval verification, enforcement, or durable evidence
before the pilot evidence supports that choice.

## Verification Baseline

The complete local verification command set is:

```bash
python -m pip install -e .
python -m compileall -q src examples evals tests dogfood
agent-governance validate --strict
agent-governance policy validate examples/policies/multi_agent_operations.json
agent-governance policy evaluate \
  examples/policies/multi_agent_operations.json \
  examples/requests/browser_read_allowed.json \
  --trusted-identity-boundary identity.reference
agent-governance policy validate dogfood/policy.json
python evals/run_eval.py
python -m unittest discover -s tests -v
```

Verified `main` contains 57 tests. Post-merge CI passed the full Python 3.9,
3.11, and 3.13 matrix at `79b7b4a9`.

On 2026-08-22, the complete local baseline passed on
`codex/dogfood-phase-1`. The branch contains 69 tests: the existing 57 tests
and 12 Phase 1 tests. The editable install, byte compilation, compatibility XML
validation, example and dogfood policy validation, reference decision, 13
documentation-recall examples, Markdown links, and all 69 tests passed. The
verification created no live observations.

## Handoff Checklist

Before ending material work:

- record the current branch, pull request, and CI outcome.
- move completed work into verified current state.
- update decisions and open questions.
- reorder the next milestone when evidence changes priority.
- record the commands and results used for verification.
- keep status claims linked to durable code, tests, issues, or pull requests.
