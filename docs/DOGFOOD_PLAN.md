# Repository Development Dogfooding Plan

- **Pilot:** Dogfood 0
- **Status:** planned, not yet running
- **Mode:** shadow; explicitly non-enforcing
- **Scope:** development of Agent Governance Harness
- **Plan date:** 2026-08-21

## Purpose

Dogfood 0 will apply the current Policy Bundle v0.1 and Decision Contract v0.1
to real development actions in this repository. The pilot will identify which
product gap creates the most operational friction before the project commits to
the next implementation milestone.

The harness will not choose the roadmap. Maintainers will use recorded
decisions, disagreements, unmapped actions, and workflow friction to choose the
next build.

## Product Boundary

The current evaluator is side-effect-free. It does not authenticate the
maintainer, verify approvals, intercept tools, enforce constraints, or retain
evidence in a trusted store.

During this pilot:

- existing user, Codex, operating-system, Git, and GitHub controls remain
  authoritative.
- a harness decision is advisory and cannot authorize an action by itself.
- `require_approval` remains unresolved inside the harness.
- user authorization is recorded only as an observed out-of-band event.
- proposed evidence is pilot data, not append-only or tamper-evident evidence.

Label the pilot **shadow** in its policy, procedure, and reports.

## Requirement Mapping

Dogfood 0 exercises implemented behavior under `AUT-001`, `AUT-003`,
`AUT-006`, `DEC-001` through `DEC-007`, `EVD-001`, `DX-003`, and `DX-006`.
It tests adoption assumptions for `DX-005`, `DX-007`, and `DX-010` without
claiming those target requirements are implemented.

Findings may change the order of future work under `DEC-008`, `APR-001` through
`APR-005`, `ENF-001` through `ENF-005`, `EVD-002`, and `DX-001` through
`DX-005`. The pilot does not satisfy those requirements.

## Governed Workflow

The first workflow is development of this repository by a human maintainer and
one or more coding agents.

### Actors and roles

The pilot policy should model these stable identities:

- `human.maintainer` is the principal and policy owner.
- `agent.developer` proposes and performs delegated development actions.
- `agent.reviewer` may inspect changes without inheriting write or publication
  authority.
- `service.github` represents the remote repository boundary.

The initial identity assertion will use a named local pilot boundary. This is a
procedural assertion, not cryptographic authentication.

The current evaluator requires an `authorized_goal_id` but does not resolve a
goal registry or authenticate the goal. The pilot must record this as an
out-of-band trust assumption.

### Capabilities and resources

The first policy should distinguish at least these actions:

| Capability | Resource | Initial shadow expectation |
| --- | --- | --- |
| Read repository content | Local repository | `allow` |
| Run local validation or tests | Local Python and CLI tools | `allow` |
| Edit documentation in an authorized task | Documentation resource | `allow` |
| Edit source or tests in an authorized task | Source and test resources | `allow` |
| Install or change a dependency | Local environment and package metadata | `require_approval` |
| Create a local commit | Local Git repository | `require_approval` |
| Push a branch or create a pull request | GitHub repository | `require_approval` |
| Merge, release, force-push, or delete remote work | GitHub repository | `deny` or `require_approval`, as the policy specifies |
| Read secrets or unrelated user data | External sensitive resource | `deny` |
| Perform an unmapped action | Unknown resource | `deny` |

Policy Bundle v0.1 uses exact resource IDs. A trusted pilot normalizer must map
concrete paths and commands to these resource classes. The observation record
must flag each case where this mapping is ambiguous or too broad.

## Baseline Scenarios

Before live observation, deterministic fixtures must cover at least:

1. allowed repository read.
2. allowed test execution.
3. allowed documentation edit within the authorized task.
4. denied edit outside the authorized task.
5. approval-gated dependency installation.
6. approval-gated local commit.
7. approval-gated branch push.
8. approval-gated pull-request creation.
9. denied or approval-gated merge.
10. denied secret access.
11. denied force-push or destructive remote action.
12. denied unmapped action.
13. denied stale identity or policy context.
14. denied malformed request.

Each scenario must declare its expected disposition and stable reason codes.
The SDK and CLI must return equivalent results.

## Shadow Procedure

For each material development action:

1. State the authorized development goal.
2. Normalize the proposed action to one capability and one resource.
3. Canonicalize the security-relevant parameters and compute
   `parameters_digest`.
4. Evaluate the request with the current shared evaluator.
5. Record the decision before the existing workflow proceeds.
6. Record the maintainer's expected disposition and any out-of-band approval.
7. Record whether the action occurred and whether the decision was useful.
8. Continue to rely on existing controls for actual execution.

An action is material when it writes repository content, changes dependencies,
creates a commit, affects remote state, deletes data, accesses sensitive data,
or delegates authority. The pilot may sample routine reads after their mapping
is stable.

## Observation Record

The pilot should retain a minimized JSONL observation for each evaluated
action. The format should contain:

- observation ID and UTC time.
- a reference to the retained canonical Action Request v0.1 and its digest.
- authorized goal, actor, capability, action, and resource IDs.
- policy bundle version, retained snapshot reference, and digest.
- Decision Result and Proposed Evidence Record references and digests.
- canonical parameter digest without raw action parameters.
- harness disposition and reason codes.
- maintainer-expected disposition.
- agreement or disagreement classification.
- whether out-of-band approval was requested and received.
- whether the action ran under the existing workflow.
- normalization time and mapping-confidence category.
- a short, non-sensitive friction code.

Do not retain raw secrets, credentials, personal data, complete prompts,
unredacted action parameters, or model chain of thought. A committed pilot
report should aggregate findings and use sanitized examples.

## Metrics

The pilot report must calculate:

- **mapping coverage:** evaluated actions divided by material actions observed.
- **decision agreement:** decisions that match the maintainer's expected
  disposition.
- **false allows:** harness `allow` results when the maintainer expected
  `deny` or `require_approval`.
- **false blocks:** harness `deny` or `require_approval` results when the
  maintainer expected `allow`.
- **approval load:** percentage of actions that return `require_approval`.
- **unmapped rate:** actions that cannot use a safe existing capability and
  resource mapping.
- **normalization effort:** median time to produce a valid request.
- **evidence completeness:** observations that can reproduce the decision from
  retained policy and normalized input.

## Stop Conditions

Stop live observation and record a blocker if:

- the harness returns an unexplained false allow.
- safe normalization requires hidden, guessed, or free-form authority.
- the observation process risks retaining a secret or unnecessary personal
  data.
- a participant mistakes a shadow decision for execution authorization.
- pilot policy must weaken fail-closed behavior to continue.

## Exit Criteria

Dogfood 0 is complete when:

- all baseline scenarios pass deterministically.
- at least 25 real material actions have been observed.
- observations cover at least six capability categories.
- every observed decision is reproducible from retained, minimized artifacts.
- each disagreement has a policy, normalization, contract, or integration
  classification.
- maintainers can rank the next three product gaps from recorded evidence.

## Next-Build Decision Rules

Use these rules after the pilot:

- Any unexplained false allow takes priority over new surface development.
- Frequent unmapped or ambiguous actions favor request normalization, resource
  selectors, or constraint work.
- High request-construction effort favors an initializer or request builder.
- Frequent unresolved `require_approval` outcomes favor Approval Grant v0.1.
- Strong decision agreement with frequent procedural bypass favors a trusted
  pre-dispatch adapter.
- Incomplete or irreproducible observations favor the evidence-sink contract.

The final selection must still map to Product Specification requirements and
pass the Product Charter anti-drift test.

## Planned Pilot Artifacts

A later implementation milestone should add:

- `dogfood/README.md` for the shadow procedure.
- `dogfood/policy.json` for repository-development governance.
- `dogfood/requests/` for deterministic baseline scenarios.
- `dogfood/expected.json` for expected outcomes and reason codes.
- `dogfood/observation.schema.json` for minimized pilot observations.
- a local recording method that retains canonical requests, decisions, and
  policy snapshots without committing live observations automatically.

These artifacts do not exist yet. Their implementation is the next recommended
action after this plan is accepted.
