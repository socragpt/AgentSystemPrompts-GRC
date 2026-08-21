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

**Status:** the Slice B decision contract is implemented; identity verification,
approval grants, enforcement, and durable evidence remain planned.

Implemented:

- Evaluate a proposed action and return `allow`, `deny`, or `require_approval`.
- Expose identical decision semantics through the Python SDK and CLI.
- Return stable reasons, effective constraints, policy provenance, and a
  proposal-only evidence record.

Remaining:

- Expose the shared evaluator through a language-neutral sidecar or service.
- Add a guided initializer, generated scenarios, and explicitly non-enforcing
  shadow mode for progressive adoption.
- Enforce tool, data, delegation, budget, time, and reversibility constraints.
- Produce append-only, redacted decision evidence tied to policy versions.

**Exit criteria:** denied actions cannot dispatch and every outcome cites the controls that produced it.

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
