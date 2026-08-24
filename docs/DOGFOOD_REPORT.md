# Dogfood 0 Pilot Report

- **Status:** live shadow observation running
- **Snapshot date:** 2026-08-23
- **Snapshot boundary:** through `observation.dogfood.022`
- **Verified `main`:** `4291a89d0d6ea7fbbbaf48607e3c5246dbc8aecf`
- **Mode:** shadow; explicitly non-enforcing

> **WARNING:** This report describes advisory decisions. It does not prove
> authorization, enforcement, compliance, or trusted evidence retention.

## Scope and Data Handling

This report aggregates the local Dogfood 0 observation log. Raw observations
remain Git-ignored under `dogfood/observations/`. They contain minimized,
digest-linked artifacts, but they are not append-only, tamper-evident, or
access-controlled evidence.

The committed report retains counts, controlled classifications, and sanitized
findings. It does not retain raw parameters, prompts, secrets, personal data,
or model chain of thought.

## Verified Snapshot

| Metric | Result |
| --- | ---: |
| Deterministic baseline scenarios | 15 of 15 passed |
| Recorded observations | 22 |
| Material actions | 17 of 25 |
| Mapping coverage | 17 of 17 material actions, or 100% |
| Capability categories observed | 10 |
| Unmapped action categories observed | 1 |
| Decision agreement | 22 of 22, or 100% |
| False allows | 0 |
| False blocks | 0 |
| Approval load | 8 of 22, or 36.4% |
| Unmapped rate | 2 of 22, or 9.1% |
| Median normalization time | 27.5 seconds |
| Reproducible retained decisions | 22 of 22, or 100% |
| v0.2 decision usefulness | 3 useful of 3 reported |
| v0.2 timestamp-order anomalies | 0 of 3 reported action times |

The recorded dispositions are 12 `allow`, eight `require_approval`, and two
`deny`. The harness did not verify approvals. The maintainer authorized the
approval-gated actions through the existing workflow, and the pilot recorded
those out-of-band events.

The two retained local branch-creation decisions used Policy Bundle snapshot
v0.1.0 and failed closed as unmapped. The current v0.2.0 pilot policy now
models one reversible, single-action local branch creation for the developer.
The retained historical decisions still reproduce against their v0.1.0 policy
snapshots. Local branch creation is not material under the current pilot
definition, so these decisions do not reduce material-action mapping coverage.

## Evidence Limits

- Observation v0.2 retains fail-closed decisions for syntactically valid JSON
  objects that fail Action Request validation. It rejects invalid JSON,
  non-object roots, and unknown request fields. The previously reported
  malformed live attempt still has no retained artifact because it occurred
  before v0.2.
- Observation v0.2 records materiality and controlled decision usefulness.
  The reporter must infer materiality for the 19 retained v0.1 records and
  labels that denominator separately.
- The recorder now generates `recorded_at` internally and stores optional
  operator-reported action time separately. One legacy v0.1 record has the
  previously reported timestamp anomaly; v0.1 has no recorder-generated time
  that can verify it.
- Observation v0.2 accepts multiple unique controlled friction codes. Legacy
  v0.1 records retain one code.
- The supported reporter validates schemas, index equality, path containment,
  artifact digests, request-validity flags, and shared-evaluator reproduction
  before it calculates metrics with explicit denominators.

These limits do not change the recorded policy disposition. They limit the
quality and completeness of pilot operations evidence.

## Next-Build Ranking Method

The completion decision ranks product gaps with four tests:

1. apply the decision rules in `DOGFOOD_PLAN.md` to verified reporter metrics;
2. prefer repeated observed friction over isolated or hypothetical gaps;
3. order prerequisite contracts before integrations that depend on them; and
4. reject any candidate that fails the Product Charter anti-drift test or
   requires the alpha to claim enforcement it does not provide.

The ranking treats approval verification, request construction and
normalization, selector precision, pre-dispatch enforcement, and evidence
retention as distinct gaps. A selected milestone may combine a request builder
with the selector support it needs, but it must not silently absorb approval,
enforcement, or evidence-store semantics. Reproducible observations lower the
priority of evidence retention; they do not satisfy the target requirements
for append-only or tamper-evident storage.

## Findings Through This Snapshot

### 1. Observation and reporting hardening is implemented

The bounded v0.2 recorder and reporter resolve the identified local experiment
gaps. They preserve v0.1 read compatibility and do not add trusted evidence
storage. The pilot must now use v0.2 for new actions and continue to test the
fields under real work.

This work maps to `EVD-001`, `EVD-004`, `DX-005`, and `DX-006`. It does not
claim that durable evidence requirements are implemented.

### 2. Request construction is operationally fragile

The pilot requires manual capability and resource selection, side-effect
vocabulary, digests, identity-boundary claims, goal claims, and timestamps.
The operator reported that one unsupported side-effect value caused a
fail-closed denial. Manual construction also produced the timestamp anomaly.

This evidence supports further evaluation of a request builder or normalizer.
It does not yet select the next product slice.

### 3. Approval remains procedural

Three real approval-gated development actions returned `require_approval`.
The maintainer authorized each through the existing workflow, but the harness
only recorded booleans. It did not create or verify an exact-bound Approval
Grant.

This is evidence relevant to `APR-002` through `APR-005`. The sample remains
too small to select approval work ahead of the other pilot findings.

### 4. Local branch creation now has a narrow pilot mapping

The current policy explicitly allows the developer to create one reversible
local branch reference on `service.local-git`. The reviewer has no delegation
for this capability. Historical unmapped decisions remain unchanged because
each observation retains its evaluated policy snapshot.

## Next Operational Milestone

Continue real repository work until the pilot reaches 25 material actions.
The current snapshot has 17. Use observation v0.2 for new attempts and run the
supported reporter before each sanitized checkpoint. Then apply the decision
rules in [`DOGFOOD_PLAN.md`](DOGFOOD_PLAN.md) and rank the next three product
gaps.

Do not add approval verification, enforcement, a decision service, or durable
evidence storage before the completed pilot supports that choice.

## Anti-Drift Review

The implemented observation-hardening milestone serves the named repository
workflow and the evidence requirements above. It reuses the shared evaluator,
keeps unsupported input fail-closed, and does not create separate policy
semantics in a report or UI. It preserves the distinction between shadow
decisions and enforcement.

## Delivery History

Pull request
[#22](https://github.com/socragpt/agent-governance-harness/pull/22) merged
Dogfood 0 Phase 1 into `main` as `39831956` on 2026-08-22 UTC. Post-merge
[`main` CI run 32599618658](https://github.com/socragpt/agent-governance-harness/actions/runs/32599618658)
passed on Python 3.9, 3.11, and 3.13.

Pull request
[#23](https://github.com/socragpt/agent-governance-harness/pull/23) merged the
first sanitized pilot checkpoint into `main` as `4291a89` on 2026-08-23 UTC.
Its pull-request CI passed on Python 3.9, 3.11, and 3.13.
