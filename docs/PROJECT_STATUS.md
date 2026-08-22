# Project Status

- **Project:** Agent Governance Harness
- **Status date:** 2026-08-21
- **Lifecycle:** early alpha
- **Repository:** <https://github.com/socragpt/agent-governance-harness>
- **Verified `main`:** `baf580d6e3ec5195c55229de73c624510d506bbf`

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
The pilot will use real workflow evidence to select the next product build
before the project commits to the full Slice C sequence.

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

## Active Milestone: Dogfood 0

The next milestone is the planned
[Repository Development Dogfooding Plan](DOGFOOD_PLAN.md). It will apply the
current evaluator to development actions in this repository.

Dogfood 0 is explicitly shadow and non-enforcing. User, Codex, operating-system,
Git, and GitHub controls remain authoritative. The pilot will not treat
evaluator output as permission to execute.

The pilot will:

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

## Open Design Questions

- Can Policy Bundle v0.1 model repository path, command, branch, and remote
  action scopes without unsafe overbreadth?
- What trusted component should normalize concrete development actions to
  exact v0.1 capability and resource IDs?
- Which observation fields are sufficient to reproduce dogfood decisions
  without retaining sensitive data?
- How should out-of-band user authorization be referenced without pretending
  that the current evaluator verified an Approval Grant?
- Which pilot finding should take priority if normalization, approval, and
  evidence gaps appear together?
- After the pilot, how should resource selectors and constraint operators be
  versioned?
- Which identity assertion verifier and enforcement adapter should become the
  first trusted references?

Resolve these questions through explicit fixtures, observations, design notes,
and tests. Do not embed unstated assumptions in an adapter.

## Next Recommended Action

Implement only the Dogfood 0 artifacts described in `DOGFOOD_PLAN.md`:

1. add the repository-development policy;
2. add deterministic scenario requests and expected results;
3. define a minimized observation record;
4. document the manual shadow procedure; and
5. validate the complete baseline before observing live actions.

Do not implement approval verification, enforcement, or durable evidence in
that milestone. Use the pilot findings to choose and plan the next product
slice.

## Verification Baseline

The complete local verification command set is:

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

The suite contains 57 tests. Before PR #20 merged, the editable install, byte
compilation, policy commands, 13 documentation-recall examples, Markdown link
checks, and all 57 tests passed locally. Post-merge `main` CI passed the full
Python 3.9, 3.11, and 3.13 matrix at `baf580d6`.

On 2026-08-21, the complete local baseline also passed after the Dogfood 0 plan
and status-document updates. This documentation milestone does not change
runtime behavior, schemas, fixtures, reason codes, or CLI contracts.

## Handoff Checklist

Before ending material work:

- record the current branch, pull request, and CI outcome.
- move completed work into verified current state.
- update decisions and open questions.
- reorder the next milestone when evidence changes priority.
- record the commands and results used for verification.
- keep status claims linked to durable code, tests, issues, or pull requests.
