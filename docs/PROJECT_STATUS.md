# Project Status

- **Project:** Agent Governance Harness
- **Status date:** 2026-08-25
- **Lifecycle:** early alpha
- **Repository:** <https://github.com/socragpt/agent-governance-harness>
- **Verified `main`:** `7c6bab7a58a793efce68e5e5ea412fce095be1f2`
- **Development branch:** `codex/mcp-shadow-v0.1` from verified `main`

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
proposal-only evidence. Approval Grant v0.1 separately returns `satisfied` or
`not_satisfied` for an exact unresolved decision under explicit caller-supplied
trust, freshness, revocation, and reuse state. Neither result dispatches or
authorizes execution.

MCP Shadow v0.1 is implemented on the local development branch. It converts a
caller-attributed MCP `tools/call` proposal into Action Request v0.1 through a
versioned exact mapping, then embeds the unchanged evaluator and optional
approval-verifier results in a mandatory non-enforcing, proposal-only envelope.
It performs no MCP networking or dispatch.

Dogfood 0 is complete through 25 material actions. The final sanitized findings
and next-build ranking are in the
[Dogfood 0 Pilot Report](DOGFOOD_REPORT.md). The pilot selected an exact-bound
Approval Grant v0.1 contract and verifier, now merged through pull request
[#27](https://github.com/socragpt/agent-governance-harness/pull/27). Verified
`main` includes that milestone, and there were no open pull requests when this
branch was cut. The next recommended product step after MCP Shadow v0.1 is a
small provider-neutral selector proposal derived from the concrete
normalization gaps, not a pre-dispatch adapter yet.

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
- normative Approval Grant, Approval Verification State, and Approval
  Verification Result v0.1 JSON Schemas.
- exact request, decision, subject, capability, resource, canonical parameter,
  policy, scope, rule, and expiry binding for approval grants.
- deterministic, side-effect-free verification of approver eligibility,
  quorum, separation of duties, freshness, caller-reported revocation, and
  caller-reported reuse state.
- equivalent approval verification through the Python SDK and CLI, with
  portable valid and fail-closed conformance examples.
- minimized proposal-only evidence for every approval-verification outcome.
- strict MCP Call Proposal, Adapter Mapping, Normalization Result, and Shadow
  Result v0.1 contracts with unknown-field rejection.
- deterministic MCP argument binding through the existing canonical parameter
  digest without coercion.
- exact caller-assigned `(server_id, tool_name)` mapping to framework-neutral
  Action Request classification fields, including duplicate-key and lifecycle
  validation.
- identical MCP normalization and shadow behavior through the SDK and CLI,
  including stable invalid-input and normalization-rejection exit codes.
- unchanged embedded Decision Result and optional Approval Verification Result
  contracts in a mandatory `mode: "shadow"`, `proposal_only: true` envelope.
- portable MCP allow, deny, approval, satisfied-grant, annotation-spoofing,
  unmapped, ambiguous, malformed, floating-point, stale, missing-context, and
  determinism fixtures.
- deterministic JSONL documentation-recall evaluation utilities.
- repository-contract, decision, approval, MCP, policy, prompt, dogfood, and
  evaluation tests.
- a human-first documentation path for users, policy authors, integrators,
  contributors, maintainers, and coding agents.

The alpha foundation does **not** implement:

- authenticated identity-to-principal binding.
- cryptographic verification of identity assertions.
- approval grant creation or collection workflows.
- authoritative revocation and reuse-state sourcing or atomic grant
  consumption.
- pre-dispatch tool or API enforcement.
- a language-neutral decision service or sidecar.
- append-only, integrity-protected decision evidence.
- policy publication, activation, revocation, or rollback.
- provider-neutral agent-framework adapters.
- authenticated or transport-bound MCP connection identity, MCP proxying, or
  MCP tool dispatch.
- behavioral or adversarial model evaluation.
- certification or compliance guarantees.

Dogfood 0 now includes:

- an exact-resource repository-development Policy Bundle v0.1;
- 15 deterministic allow, deny, approval, stale, malformed, unmapped, and
  local-branch Action Request fixtures;
- expected dispositions, reason codes, cited controls, and approval
  requirements for each fixture;
- a closed v0.2 observation schema and retained v0.1 read compatibility;
- a dependency-free local recorder for valid and invalid request objects,
  policy snapshots, decisions, and proposal-only evidence artifacts;
- recorder-generated UTC time, optional operator-reported action time, logical
  activity IDs, explicit materiality, controlled decision usefulness, and
  multiple controlled friction codes;
- a dependency-free reporter that validates schemas, index equality, path
  containment, digests, request-validity flags, and shared-evaluator
  reproduction before it calculates metrics;
- a narrow developer-only policy mapping for one reversible local branch
  creation;
- a manual shadow procedure with an explicit live-observation gate; and
- 17 dogfood tests for policy validity, decisions, SDK/CLI parity,
  determinism, fail-closed behavior, observation compatibility, recording,
  reporting, corruption detection, and reproduction.

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

Pull request
[#22](https://github.com/socragpt/agent-governance-harness/pull/22) merged
Dogfood 0 Phase 1 into `main` as `39831956` on 2026-08-22 UTC. It added the
repository-development policy, 14 deterministic scenarios, the minimized
observation contract and recorder, the live-gated procedure, and 12 tests. It
did not change the shared evaluator or add enforcement. Post-merge
[`main` CI run 32599618658](https://github.com/socragpt/agent-governance-harness/actions/runs/32599618658)
passed on Python 3.9, 3.11, and 3.13.

Pull request
[#23](https://github.com/socragpt/agent-governance-harness/pull/23) merged the
first sanitized Dogfood 0 status checkpoint into `main` as `4291a89` on
2026-08-23 UTC. It recorded verified findings through
`observation.dogfood.012` without changing evaluator or policy semantics. The
pull-request CI run passed on Python 3.9, 3.11, and 3.13.

Pull request
[#24](https://github.com/socragpt/agent-governance-harness/pull/24) merged the
Dogfood 0 observation-hardening milestone into `main` as `ca34507` on
2026-08-24 UTC. It added the v0.2 observation contract, retained v0.1 read
compatibility, the supported reporter, invalid-request retention, the narrow
local-branch mapping, and 17 dogfood tests. Pull-request
[CI run 32752158332](https://github.com/socragpt/agent-governance-harness/actions/runs/32752158332)
and post-merge
[`main` CI run 32752296025](https://github.com/socragpt/agent-governance-harness/actions/runs/32752296025)
passed on Python 3.9, 3.11, and 3.13, including wheel builds and installed-wheel
smoke tests.

Pull request
[#25](https://github.com/socragpt/agent-governance-harness/pull/25) merged the
Dogfood 0 completion checkpoint into `main` as `11257449` on 2026-08-24 UTC.
It published the frozen evidence snapshot, ranked the next three product gaps,
and selected Approval Grant v0.1 as the next milestone. It did not change
schemas, evaluator behavior, policy semantics, or enforcement behavior.
Pull-request
[CI run 32771755851](https://github.com/socragpt/agent-governance-harness/actions/runs/32771755851)
and post-merge
[`main` CI run 32771899229](https://github.com/socragpt/agent-governance-harness/actions/runs/32771899229)
passed on Python 3.9, 3.11, and 3.13. Each job built a wheel and smoke-tested
the installed package.

Pull request
[#26](https://github.com/socragpt/agent-governance-harness/pull/26) merged the
post-dogfood status handoff into `main` as `d74173d7` on 2026-08-24 UTC. It
published the verified completion state and next-milestone handoff without
changing schemas or runtime behavior. Its pull-request checks passed.
Post-merge
[`main` CI run 32776110635](https://github.com/socragpt/agent-governance-harness/actions/runs/32776110635)
passed on Python 3.9, 3.11, and 3.13, including wheel builds and installed-wheel
smoke tests.

Pull request
[#27](https://github.com/socragpt/agent-governance-harness/pull/27) merged
Approval Grant v0.1 into `main` as `2ce10f5c` on 2026-08-25 UTC. It delivered
the normative grant, verification-state, and verification-result contracts;
the deterministic SDK and CLI verifier; portable conformance examples;
fail-closed tests; and aligned public documentation. Pull-request
[CI run 32786290069](https://github.com/socragpt/agent-governance-harness/actions/runs/32786290069)
and post-merge
[`main` CI run 32804325065](https://github.com/socragpt/agent-governance-harness/actions/runs/32804325065)
passed on Python 3.9, 3.11, and 3.13. Each job built and smoke-tested the wheel.

## Completed Milestone: Dogfood 0

The [Repository Development Dogfooding Plan](DOGFOOD_PLAN.md) records the
completed milestone. Phase 1 built the policy, fixtures, expected results,
observation contract, recorder, procedure, and tests. The Phase 1 artifacts met
their acceptance criteria and are merged into `main`.

Dogfood 0 is explicitly shadow and non-enforcing. User, Codex, operating-system,
Git, and GitHub controls remain authoritative. The pilot did not treat
evaluator output as permission to execute.

The completed pilot:

1. modeled repository-development actors, capabilities, resources, controls, and
   approval expectations in Policy Bundle v0.1;
2. created deterministic allow, deny, approval, stale, malformed, and unmapped
   scenarios;
3. observed 25 real material development actions across ten
   capability categories;
4. recorded minimized decisions, expected outcomes, disagreements, and workflow
   friction; and
5. used the evidence to rank the next three product gaps.

The pilot tested adoption assumptions for `DX-005`, `DX-007`, and `DX-010`. It
does not claim those target requirements are implemented.

No live development observations were collected during Phase 1. The maintainer
opened the live gate after reviewing the verified Phase 1 result. The first
observed material action recorded that authorization in this status document.
Harness results remain advisory and do not authorize execution.

The Phase 1 anti-drift review passed. The work serves the named repository
workflow, reuses the shared policy and decision semantics, preserves
fail-closed behavior, keeps trust assumptions explicit, remains
framework-neutral, and produces reproducible artifacts. The documentation does
not describe shadow decisions as enforcement or verified approval.

The verified completion snapshot through `observation.dogfood.031` contains 31
observations and 25 material actions. All 25 material actions had a safe
capability and resource mapping, so mapping coverage is 100%. Ten capability
categories and one historically unmapped action category were observed. All
31 retained decisions reproduce and match the maintainer's expected policy
disposition. The snapshot has zero false allows and zero false blocks. All 12
v0.2 records classify their decisions as useful. See the
[Dogfood 0 Pilot Report](DOGFOOD_REPORT.md) for metrics, evidence limits, the
ranked gaps, and the selected next milestone.

## Completed Milestone: Approval Grant v0.1

The merged Approval Grant v0.1 milestone implements the first ranked post-pilot
gap under `APR-002` through `APR-005`. It adds strict versioned contracts for
Approval Grant, Approval Verification State, Approval Verification Result, and
embedded proposal-only verification evidence. One deterministic verifier is
exposed through the `agent_governance` SDK and `agent-governance approval
verify` CLI.

The verifier reevaluates the exact policy and request, requires the supplied
Decision Result to match and remain `require_approval`, checks every request,
decision, subject, capability, resource, parameter, policy, scope, rule, and
expiry binding, and derives approver eligibility from policy roles. Quorum,
separation of duties, approver identity freshness, caller-reported revocation,
and caller-reported reuse all fail closed. Portable examples cover valid,
stale, mismatched, insufficient-quorum, self-approved, revoked, and reused
grants.

The core is side-effect-free. It neither creates nor collects approvals, reads
the clock or network, sources authoritative identity or grant state, consumes
a single-use grant, changes Decision Result v0.1, dispatches an action, nor
retains trusted evidence. Its Product Charter anti-drift review passes: it
serves the named governance problem, reuses the shared core, preserves exact
fail-closed contracts, keeps trust inputs explicit, remains framework-neutral,
and does not claim enforcement or compliance.

## Completed Local Milestone: MCP Shadow v0.1

The `codex/mcp-shadow-v0.1` branch implements the first versioned MCP
integration profile under `INT-001` through `INT-003`, `DX-003`, `DX-005`,
`DX-009`, `AUT-001`, existing `DEC-001`/`003`/`005`/`006`, existing
`APR-002` through `APR-004`, `EVD-001`, and `TST-001`.

One pure normalizer combines an MCP Call Proposal v0.1 and an MCP Adapter
Mapping v0.1. Caller identity, acting actor, goal, time, connection ID, tool
name, and arguments remain distinct from mapping-owned policy classification.
Unknown, duplicate, ambiguous, not-yet-effective, stale, unmapped,
uncanonicalizable, or incomplete inputs fail closed with sorted `mcp.*` reasons
and JSON Pointer paths. The constructed Action Request passes the existing
validator and produces byte-identical decisions to its hand-authored
equivalent.

The shadow evaluator calls the unchanged decision evaluator and optional
approval verifier. A satisfied approval stays nested while the disposition and
CLI exit remain `require_approval`. The envelope and its minimized evidence are
always proposal-only and never retain raw arguments or raw annotations.

The Product Charter anti-drift review passes:

1. It serves the named request-construction gap for tool-using agents.
2. It strengthens the path from caller-attributed intent to a reproducible
   decision and minimized evidence proposal.
3. It preserves fail-closed behavior, least privilege, and existing delegation
   semantics.
4. It makes principal, acting actor, goal, connection identity, mapping
   provenance, and lifecycle explicit instead of inferring them from MCP
   metadata.
5. MCP details remain in versioned adapter artifacts; the core Action Request,
   Decision Result, Approval Verification Result, and policy semantics remain
   provider-neutral.
6. Portable fixtures and SDK/CLI parity tests reproduce every outcome.
7. Documentation labels the entire reference as shadow, proposal-only, and
   non-enforcing.
8. The implementation reuses one normalizer, evaluator, verifier, reason
   vocabulary, and evidence boundary instead of creating competing policy
   semantics.

Observed normalization gaps are now concrete. Action Request v0.1 binds the
complete argument object by digest but Policy Bundle v0.1 cannot match values
inside it. One exact tool mapping therefore cannot safely distinguish URLs,
recipients, paths, commands, branches, remotes, or argument-selected resources.
Policy also cannot verify mapping-declared side effects against capability
metadata. These findings inform `DEC-008`, `PTH-001`, and `AUT-002`; the branch
does not implement those target requirements or any `ENF-*` requirement.

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
12. **Let dogfood evidence select the next build.** The completed pilot ranks
    Approval Grant v0.1 first, request construction and selectors second, and a
    trusted pre-dispatch adapter third.
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
18. **Version local observation evidence.** New records use the closed v0.2
    contract. The reporter reads v0.1 records without rewriting them and labels
    legacy inferred materiality.
19. **Model local branch creation narrowly.** The developer can create one
    reversible local branch reference. The reviewer does not receive this
    delegation, and retained v0.1.0 policy snapshots preserve historical
    unmapped denials.
20. **Verify approval before attempting enforcement.** Approval Grant v0.1 is
    a provider-neutral, deterministic verifier, not an approval workflow UI or
    tool-dispatch adapter.
21. **Use MCP as the first wedge, not the semantic center.** The next reference
    integration normalizes MCP call proposals in non-enforcing shadow mode.
    Core request, decision, approval, and evidence contracts remain framework-
    neutral, and MCP metadata is not authority by default.
22. **Keep acting actor context caller-supplied.** MCP does not establish the
    relationship between an authorizing principal and acting actor. Mapping
    that relationship would invent authority, so MCP Call Proposal v0.1 carries
    a separate caller-attributed `actor_id`.
23. **Digest annotations without trusting them.** The full proposal digest
    changes when annotations change, but request construction excludes them so
    the Action Request and decision stay byte-identical.
24. **Do not hide selector gaps in argument parsing.** v0.1 binds arguments by
    digest and records exact mapping gaps; it does not infer destinations,
    resources, or side effects from free-form values.

## Open Design Questions and Findings

- Policy Bundle v0.1 cannot model repository path, command, branch, or remote
  selectors. Dogfood 0 uses exact resource classes and records ambiguous or
  overbroad normalization as a finding.
- What trusted component should normalize concrete development actions to
  exact v0.1 capability and resource IDs?
- The Phase 1 observation contract can reproduce a decision from minimized,
  digest-linked artifacts. Live use must test whether its controlled fields
  are operationally sufficient.
- Historical dogfood observations record whether an out-of-band approval was
  requested and received. They were not backfilled with or reclassified as
  verified Approval Grants after Approval Grant v0.1 was implemented.
- Policy Bundle v0.1 does not bind a resource class to concrete path, command,
  branch, or remote parameters. The pilot normalizer must preserve that limit.
- Action Request v0.1 retains expected side effects, but Policy Bundle v0.1
  does not declare a comparable capability-side-effect contract.
- The named identity boundary and authorized goal remain procedural inputs.
  The current evaluator does not verify either claim.
- Observation v0.2 makes materiality and decision usefulness explicit. The
  reporter still infers materiality for the 19 retained v0.1 records and labels
  that denominator.
- The operator-reported malformed live attempt occurred before v0.2 and still
  has no retained artifact. New syntactically valid JSON objects that fail
  Action Request validation can be retained. Invalid JSON, non-object roots,
  and unknown request fields remain outside the recorder scope.
- One legacy v0.1 timestamp anomaly remains unverifiable because v0.1 has no
  recorder-generated timestamp. New records separate generated `recorded_at`
  from optional operator-reported action time.
- Approval Grant v0.1 resolves changing verification inputs as explicit caller
  state and returns a separate `satisfied` or `not_satisfied` contract without
  changing the three-way Decision Result. A trusted state-provider interface
  and atomic consumption remain integration work.
- After the pilot, how should resource selectors and constraint operators be
  versioned?
- MCP server and tool keys, arguments digest, caller principal and actor, goal,
  time, constraints, and mapping-owned classification normalize without loss.
  Concrete values within arguments require a future selector or request-
  contract version when policy must distinguish them.
- Which smallest selector vocabulary can cover observed destinations,
  recipients, paths, commands, branches, and remotes without adding a general
  expression language or MCP-specific semantics to the core?
- Which identity assertion verifier should become the first trusted reference
  after the MCP shadow profile exposes its concrete trust-boundary needs?

Resolve these questions through explicit fixtures, observations, design notes,
and tests. Do not embed unstated assumptions in an adapter.

## Next Recommended Action

Specify the smallest provider-neutral selector or request-contract change
needed for concrete values inside tool arguments, using the MCP v0.1 fixtures
as evidence. Map each proposed field to `DEC-008` or `PTH-001`, define exact and
fail-closed matching, and preserve v0.1 compatibility. Do not attempt a trusted
pre-dispatch adapter until the selected fields can be represented and tested
without free-form inference.

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
agent-governance approval verify --help
agent-governance mcp normalize \
  examples/mcp/mapping.json \
  examples/mcp/proposals/browser-read.json
agent-governance mcp shadow \
  examples/policies/multi_agent_operations.json \
  examples/mcp/mapping.json \
  examples/mcp/proposals/browser-read.json \
  --trusted-identity-boundary identity.reference
agent-governance policy validate dogfood/policy.json
python evals/run_eval.py
python -m unittest discover -s tests -v
```

Verified `main` at `7c6bab7a` contains 85 tests. Post-merge CI run
`32805097492` passed the full Python 3.9, 3.11, and 3.13 matrix. Earlier
Approval Grant pull-request and post-merge CI also passed that matrix. Each job
performed a clean installation, byte compilation, compatibility XML
validation, example policy validation, reference evaluation, all 13
documentation-recall examples, and all 85 tests. Each job also built and
smoke-tested the wheel, including the installed Approval Grant CLI surface.
The MCP branch adds 15 tests, bringing the full local count to 100.

The complete local baseline passed on 2026-08-25: editable install, byte
compilation, compatibility XML strict validation, example and dogfood policy
validation, reference evaluation, approval help, both MCP commands, all 13
documentation-recall examples, and all 100 unit tests. The macOS system Python
attempted to place bytecode in a sandbox-blocked user cache, so the successful
compile used `PYTHONPYCACHEPREFIX=/tmp/agh-baseline-pyc`; source coverage was
unchanged.

Wheel `agent_governance_harness-0.1.0-py3-none-any.whl` was built with SHA-256
`0427f897f5732a17ac863114e1b2a178f257e8ee4b2a3593814258c660293fc1`,
installed into an isolated environment outside the repository, and smoke-
tested there. XML strict validation exited `0`; MCP normalize exited `0`; MCP
allow shadow exited `0`; and satisfied-approval shadow exited `3` while keeping
the embedded disposition `require_approval` and verification outcome
`satisfied`. JSON parsing, Markdown links, and `git diff --check` also passed.

The completed local milestone baseline also covered dogfood policy validation,
valid and stale approval CLI exit codes `0` and `5`, JSON validation, Markdown
link checks, diff checks, and an exact valid approval verification from an
installed wheel outside the repository.

The supported reporter also verified the maintainer's ignored local records
through `observation.dogfood.039`: 39 observations, 32 material actions, 100%
material-action mapping coverage, 100% decision agreement, 100% evidence
completeness, zero false allows, and zero false blocks. These local follow-up
records do not change the published completion snapshot. The report remains
frozen at `observation.dogfood.031`, where the pilot first reached 25 material
actions.

## Handoff Checklist

Before ending material work:

- record the current branch, pull request, and CI outcome.
- move completed work into verified current state.
- update decisions and open questions.
- reorder the next milestone when evidence changes priority.
- record the commands and results used for verification.
- keep status claims linked to durable code, tests, issues, or pull requests.
