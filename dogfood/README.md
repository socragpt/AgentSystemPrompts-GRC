# Dogfood 0: Repository-Development Shadow Pilot

> **WARNING: THIS PILOT IS NON-ENFORCING.** A harness decision is not
> authorization to execute an action. Existing user, Codex, operating-system,
> Git, and GitHub controls remain authoritative.

Dogfood 0 applies Policy Bundle v0.1 and Decision Contract v0.1 to development
of this repository. The pilot measures decision quality, normalization effort,
and evidence completeness. It does not dispatch actions, verify approvals, or
retain trusted evidence.

## Phase Gate

Phase 1 builds and validates the pilot artifacts. **Do not record live
development actions during Phase 1.** The maintainer must explicitly authorize
live shadow observation after all Phase 1 acceptance checks pass.

The repository contained no live observations at the end of Phase 1. The
maintainer opened the live gate on 2026-08-22 after the complete baseline
passed. The pilot is now running in shadow mode. Live records remain ignored by
Git under `dogfood/observations/`.

## Pilot Artifacts

- `policy.json` models the repository-development actors, resources,
  capabilities, delegations, controls, and approval requirements.
- `requests/` contains the 14 deterministic baseline Action Request fixtures.
- `expected.json` declares the expected disposition, reason codes, cited
  controls, and approval requirements for each fixture.
- `observation.schema.json` defines a closed, minimized observation record.
- `record_observation.py` creates canonical local artifacts and a JSONL index.
  It does not run Git or commit its output.

## Policy Choices

The Phase 1 policy makes these explicit choices:

| Proposed action | Shadow disposition |
| --- | --- |
| Read repository content | `allow` |
| Run local validation or tests | `allow` |
| Edit task-scoped documentation, source, or tests | `allow` |
| Install or change a dependency | `require_approval` |
| Create a local commit | `require_approval` |
| Push a branch or create a pull request | `require_approval` |
| Merge a pull request | `require_approval` |
| Force-push, delete remote work, or create a release | `deny` |
| Read secrets or unrelated sensitive data | `deny` |
| Edit content outside the authorized task | `deny` |
| Use an unmapped capability or resource | `deny` through the bundle default |

The reviewer receives repository-read and local-validation delegations only.
The reviewer does not receive edit, dependency, commit, publication, merge, or
destructive-remote capabilities.

## Current Trust and Modeling Limits

Policy Bundle v0.1 uses exact resource IDs. It does not select filesystem
paths, commands, branches, or remotes. A pilot participant must map each
concrete action to one exact capability and resource before evaluation. Record
an ambiguous or overbroad mapping as friction. Do not broaden authority to make
the request pass.

The pilot uses `identity.dogfood-local` as a named identity boundary. This name
is a procedural assertion, not cryptographic authentication. The evaluator
also accepts `authorized_goal_id` without resolving a goal registry. Existing
task instructions remain the authority for the goal and action scope.

`require_approval` is an unresolved decision. The harness does not create or
verify an Approval Grant. Record a maintainer decision only as an observed,
out-of-band event.

The recorder produces local files. It does not provide append-only,
tamper-evident, access-controlled, or trusted evidence retention.

## Validate Phase 1

Run these commands from the repository root:

```bash
agent-governance policy validate dogfood/policy.json
python -m unittest tests.test_dogfood -v
```

The dogfood test evaluates every case through the SDK and CLI. It also checks
determinism, stale-policy behavior, fail-closed cases, the observation schema,
artifact digests, and decision reproduction.

## Live Shadow Procedure

Use this procedure only after the maintainer explicitly authorizes live shadow
observation.

For each material action:

1. State the authorized development goal.
2. Identify the concrete proposed action before it occurs.
3. Map the action to one exact capability and resource in `policy.json`.
4. Canonicalize the security-relevant parameters and compute
   `parameters_digest`.
5. Create a valid Action Request v0.1.
6. Evaluate the request with `identity.dogfood-local` as the procedural trust
   boundary.
7. Show the disposition, reason codes, effective constraints, and the
   non-enforcing warning to the maintainer.
8. Use the existing workflow to decide whether the action proceeds.
9. Record the maintainer's expected disposition and any out-of-band approval.
10. Record whether the action occurred, the mapping confidence, normalization
    time, and one non-sensitive friction code.

An action is material when it writes repository content, changes dependencies,
creates a commit, affects remote state, deletes data, accesses sensitive data,
or delegates authority. Routine reads can be sampled after their mapping is
stable.

## Local Recorder

After the live gate opens, use the ignored `dogfood/observations/` directory or
an output directory outside the repository. Do not write live records to a
tracked path. Run the recorder with a retained canonical request:

```bash
pilot_output="dogfood/observations"
python dogfood/record_observation.py \
  --policy dogfood/policy.json \
  --request path/to/canonical-request.json \
  --output-dir "$pilot_output" \
  --observation-id observation.dogfood.001 \
  --observed-at 2026-08-22T20:00:00Z \
  --trusted-identity-boundary identity.dogfood-local \
  --expected-disposition allow \
  --action-occurred yes \
  --normalization-duration-ms 45000 \
  --mapping-confidence exact \
  --friction-code none
```

Add `--approval-requested` and `--approval-received` only when those events
occurred through the existing workflow. These flags record observations. They
do not verify an approval or authorize execution.

The recorder creates this structure:

```text
<output-dir>/
  observations.jsonl
  observation.dogfood.001/
    observation.json
    artifacts/
      request.json
      policy.json
      decision.json
      proposed-evidence.json
```

The request and policy artifact digests match the digests in the Decision
Result. The decision and proposed-evidence digests bind the observation to the
retained files.

## Data-Minimization Rule

Do not put secrets, credentials, personal data, complete prompts, raw action
parameters, security-sensitive payloads, or model chain of thought in an
observation. The schema allows identifiers, controlled classifications, event
booleans, artifact references, and digests. It rejects unknown fields.

Stop observation if safe normalization needs hidden or guessed authority. Stop
if the record can expose sensitive data. Stop if a participant treats a shadow
decision as execution authorization.

## Pilot Review

After at least 25 material observations across at least six capability
categories, calculate the metrics in
[`docs/DOGFOOD_PLAN.md`](../docs/DOGFOOD_PLAN.md). Rank the next three product
gaps from the retained evidence. Do not select the next build from anecdote or
from the harness disposition alone.

The committed [Dogfood 0 Pilot Report](../docs/DOGFOOD_REPORT.md) contains the
current sanitized checkpoint. Raw observations remain local and ignored.
