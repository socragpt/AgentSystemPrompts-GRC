# Dogfood 0 Pilot Report

- **Status:** live shadow observation running
- **Snapshot date:** 2026-08-22
- **Snapshot boundary:** through `observation.dogfood.012`
- **Verified `main`:** `39831956cfcbb88f2dc75fd05548aec5ca26d707`
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
| Deterministic baseline scenarios | 14 of 14 passed |
| Recorded observations | 12 |
| Material actions | 8 of 25 |
| Mapping coverage | 8 of 8 material actions, or 100% |
| Modeled capability categories observed | 7 |
| Unmapped action categories observed | 1 |
| Decision agreement | 12 of 12, or 100% |
| False allows | 0 |
| False blocks | 0 |
| Approval load | 3 of 12, or 25% |
| Unmapped rate | 1 of 12, or 8.3% |
| Median normalization time | 20 seconds |
| Reproducible retained decisions | 12 of 12, or 100% |
| Timestamp-order anomalies | 1 |

The recorded dispositions are eight `allow`, three `require_approval`, and one
`deny`. The three approval-gated actions were a local commit, a branch push,
and pull-request creation. The harness did not verify their approvals. The
maintainer authorized those actions through the existing workflow, and the
pilot recorded that out-of-band event.

The unmapped local branch creation was not a material action under the current
pilot definition. It changed a reversible local Git reference, not repository
content or remote state. It therefore does not reduce mapping coverage for the
eight material actions in this snapshot.

## Evidence Limits

- The recorder rejects invalid Action Requests. The operator reported one
  malformed live request with a `request.schema.enum` denial. The recorder
  could not retain the denial through its normal path. No retained pilot
  artifact independently reproduces this event.
- The observation contract does not explicitly mark a material action or say
  whether the decision was useful. The current material count is inferred from
  the governed capability. Decision usefulness remains unmeasured.
- The recorder accepts an operator-supplied observation timestamp. One record
  is out of sequence because the supplied time was later than the recorder
  invocation.
- Each observation accepts only one friction code, although one action can
  expose more than one problem.
- The current report required a separate local verification query. The pilot
  has no supported aggregate-report command.

These limits do not change the recorded policy disposition. They limit the
quality and completeness of pilot operations evidence.

## Findings Through This Snapshot

### 1. Observation and reporting need hardening

Every retained decision is reproducible, but the recorder cannot retain every
decision attempt. It also depends on manual timestamps and inferred reporting
fields. This is the clearest blocker to completing Dogfood 0 with reliable
metrics.

This finding maps to `EVD-001`, `EVD-004`, `DX-005`, and `DX-006`. It does not
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

### 4. The pilot policy does not cover the full repository workflow

Local branch creation is not a modeled capability. Its valid Action Request
failed closed with `authority.capability_not_found`. The existing workflow
still allowed the reversible local action because Dogfood 0 is non-enforcing.

The next pilot update must either model local branch creation explicitly or
classify it as outside the observed workflow. It must not broaden authority
implicitly.

## Next Operational Milestone

Complete a bounded **Dogfood 0 observation-hardening** change before resuming
high-volume observation:

1. retain fail-closed decisions for invalid Action Requests without treating
   invalid input as executable authority;
2. generate recording time inside the recorder and distinguish it from the
   operator-reported action time;
3. record materiality and decision usefulness explicitly;
4. preserve more than one controlled friction finding when necessary;
5. add a supported aggregate report that verifies artifact digests and
   decision reproduction; and
6. decide explicitly whether local branch creation belongs in the pilot policy.

This milestone improves the experiment. It does not add approval verification,
enforcement, a decision service, or durable evidence storage.

After this change, continue real repository work until the pilot reaches 25
material actions. Then apply the decision rules in
[`DOGFOOD_PLAN.md`](DOGFOOD_PLAN.md) and rank the next three product gaps.

## Anti-Drift Review

The proposed observation-hardening milestone serves the named repository
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
