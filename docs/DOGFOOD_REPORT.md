# Dogfood 0 Pilot Report

- **Status:** complete; next-build decision recorded
- **Snapshot date:** 2026-08-24
- **Snapshot boundary:** through `observation.dogfood.031`
- **Verified `main`:** `11257449ebe609c944e1a70ff705959fe0051db5`
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
| Recorded observations | 31 |
| Material actions | 25 of 25 |
| Mapping coverage | 25 of 25 material actions, or 100% |
| Capability categories observed | 10 |
| Unmapped action categories observed | 1 |
| Decision agreement | 31 of 31, or 100% |
| False allows | 0 |
| False blocks | 0 |
| Approval load | 14 of 31, or 45.2% |
| Unmapped rate | 2 of 31, or 6.5% |
| Median normalization time | 30 seconds |
| Reproducible retained decisions | 31 of 31, or 100% |
| v0.2 decision usefulness | 12 useful of 12 reported |
| v0.2 timestamp-order anomalies | 0 of 12 reported action times |

The recorded dispositions are 15 `allow`, 14 `require_approval`, and two
`deny`. The harness did not verify approvals. The maintainer authorized all 14
approval-gated decisions through the existing workflow, and 13 of those
actions occurred. The pilot recorded authorization only as an out-of-band
event.

The two retained local branch-creation decisions used Policy Bundle snapshot
v0.1.0 and failed closed as unmapped. The current v0.2.0 pilot policy now
models one reversible, single-action local branch creation for the developer.
The retained historical decisions still reproduce against their v0.1.0 policy
snapshots. Local branch creation is not material under the current pilot
definition, so these decisions do not reduce material-action mapping coverage.
The first live request evaluated against v0.2.0 returned `allow` for the
developer's reversible, single-action branch creation and matched the
maintainer's expectation.

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

### 1. Approval is the largest unresolved control-path gap

Fourteen of 31 observations, or 45.2%, returned `require_approval`. Every one
depended on existing out-of-band authorization because the harness cannot
create or verify a grant. `approval-unverified` is the most frequent controlled
friction code, with 14 occurrences.

This evidence selects an Approval Grant v0.1 contract and verifier as the next
milestone under `APR-002` through `APR-005`. Approval verification is a
prerequisite for a trusted adapter: an adapter cannot safely dispatch the
current approval-gated workload while approval remains only a boolean in an
observation.

### 2. Request construction and normalization remain costly

`request-construction` occurred 13 times, the median normalization time was 30
seconds, `goal-assumption` occurred nine times, and `identity-assumption`
occurred eight times. The pilot required manual capability and resource
selection, side-effect vocabulary, digests, identity-boundary claims, goal
claims, and timestamps.

The second-ranked gap is a request builder and trusted normalizer with richer
selector support under `DX-001`, `DEC-008`, and `PTH-001`. Policy Bundle v0.1
cannot select concrete paths, commands, branches, or remotes; four observations
explicitly recorded `selector-too-broad`. The builder must expose that limit
instead of guessing authority.

### 3. Enforcement should follow approval and normalization

All 31 decisions matched the maintainer's expected disposition, with no false
allows or false blocks. Existing workflow controls, not the harness, decided
whether actions occurred. This combination favors one trusted pre-dispatch
reference adapter under `DX-004` and `ENF-001` through `ENF-005`, but only after
the approval and normalization prerequisites above exist.

### 4. Local evidence quality is sufficient for milestone selection

All 31 observations reproduced from minimized request and policy artifacts,
and the reporter found complete evidence for every record. This lowers the
relative priority of an evidence-sink contract. It does not satisfy `EVD-002`
or `EVD-003`: the local files are still ignored, mutable, and not a trusted
append-only store.

### 5. The narrow local-branch mapping works but exposes selector limits

The current policy allowed the developer's first live reversible local-branch
request and continued to deny the retained v0.1.0 unmapped requests against
their historical policy snapshots. The reviewer still has no branch-creation
delegation. The live mapping was useful, but its generic local-Git resource
also contributed one `selector-too-broad` finding.

## Final Gap Ranking

1. **Approval Grant v0.1 contract and verifier.** Highest frequency, direct
   safety impact, and a prerequisite for approval-gated enforcement.
2. **Request builder and trusted normalizer with richer selectors.** Repeated
   construction friction and the largest source of manual trust assumptions.
3. **Trusted pre-dispatch reference adapter.** Strong decision agreement makes
   integration useful, but it depends on the first two gaps.

The language-neutral decision service and durable evidence sink remain target
work. The pilot did not produce evidence that they should displace these three
gaps.

## Next Operational Milestone

Implement Approval Grant v0.1 as a versioned, provider-neutral contract plus a
deterministic, side-effect-free verifier. It must bind the exact subject,
capability, resource, parameter digest, decision, policy, scope, and expiry;
validate approver eligibility, quorum, separation of duties, and explicit
revocation or reuse state; and fail closed for every missing, stale,
mismatched, insufficient, self-approved, revoked, or reused grant.

Expose equivalent verification through the Python SDK and CLI with shared
conformance fixtures and proposal-only evidence. Do not collect approvals,
dispatch actions, enforce constraints, or claim durable evidence in this
milestone.

## Anti-Drift Review

The selected milestone serves the observed approval-gated repository workflow
and strengthens the path from an explicit `require_approval` decision to an
exact, testable authorization artifact. Invalid or ambiguous grants fail
closed, delegation does not expand, and approval authority remains explicit.
The contract and verifier remain provider-neutral, use the shared decision and
policy identifiers, and can be tested deterministically. Documentation will
continue to distinguish verification from collection, dispatch, enforcement,
and trusted retention. The milestone therefore passes the Product Charter
anti-drift test without creating a competing policy interpretation.

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

Pull request
[#24](https://github.com/socragpt/agent-governance-harness/pull/24) merged the
observation-hardening milestone into `main` as `ca34507` on 2026-08-24 UTC.
Pull-request
[CI run 32752158332](https://github.com/socragpt/agent-governance-harness/actions/runs/32752158332)
and post-merge
[`main` CI run 32752296025](https://github.com/socragpt/agent-governance-harness/actions/runs/32752296025)
passed on Python 3.9, 3.11, and 3.13.

Pull request
[#25](https://github.com/socragpt/agent-governance-harness/pull/25) merged this
completion checkpoint into `main` as `11257449` on 2026-08-24 UTC. Pull-request
[CI run 32771755851](https://github.com/socragpt/agent-governance-harness/actions/runs/32771755851)
and post-merge
[`main` CI run 32771899229](https://github.com/socragpt/agent-governance-harness/actions/runs/32771899229)
passed on Python 3.9, 3.11, and 3.13. Each job built a wheel and smoke-tested
the installed package.
