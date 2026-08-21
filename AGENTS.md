# Agent Working Agreement

This file is the entry point for coding agents and fresh context windows working
on Agent Governance Harness.

## Start Every Fresh Context

1. Read [`docs/PRODUCT_CHARTER.md`](docs/PRODUCT_CHARTER.md) for the durable
   purpose, constitutional principles, boundaries, and anti-drift test.
2. Read [`docs/PRODUCT_SPEC.md`](docs/PRODUCT_SPEC.md) for target workflows,
   requirements, acceptance scenarios, and the definition of a complete
   reference product.
3. Read [`README.md`](README.md) for the implemented product promise and current
   boundary.
4. Read [`docs/PROJECT_STATUS.md`](docs/PROJECT_STATUS.md) for the latest
   project snapshot, active work, decisions, and next priorities.
5. Read [`ROADMAP.md`](ROADMAP.md),
   [`docs/ARCHITECTURE.md`](docs/ARCHITECTURE.md), and
   [`docs/SAFETY_MODEL.md`](docs/SAFETY_MODEL.md) before changing behavior.
6. Inspect the current Git branch, working tree, recent commits, and open pull
   requests. Do not assume the last conversation's branch or PR state is still
   current.
7. Treat implementation and tests as authoritative when they disagree with a
   status document, then update the status document in the same change.

## Product Guardrails

- The project is a framework-neutral, policy-as-code governance harness for
  authority, delegation, approvals, constraints, and evidence requirements in
  multi-agent systems.
- [`docs/PRODUCT_CHARTER.md`](docs/PRODUCT_CHARTER.md) is the stable authority
  for product purpose and boundaries. Architecture and implementation must
  conform to it rather than redefine it implicitly.
- The current compiler emits deterministic policy artifacts. It does **not**
  authorize or dispatch runtime actions.
- The target product exposes one shared governance engine through a guided
  initializer, CLI, embedded SDK, decision service, and enforcement adapters.
  These surfaces must not develop different policy semantics.
- Missing, stale, ambiguous, or conflicting authority must fail closed.
- Delegation must not create authority the delegator does not possess.
- The XML prompt is a compatibility path; Policy Bundle v0.1 is the structured
  path forward.
- Preserve the `agent_governance` Python import and `agent-governance` CLI unless
  a deliberate compatibility change is approved.
- Do not claim certification, legal compliance, or safety guarantees.

## Change Discipline

- Prefer one reviewable milestone per branch and pull request.
- Map material product work to requirement IDs in
  [`docs/PRODUCT_SPEC.md`](docs/PRODUCT_SPEC.md) and run the
  [charter anti-drift test](docs/PRODUCT_CHARTER.md#anti-drift-test).
- Keep schemas, examples, documentation, tests, and compiled behavior aligned.
- Add precise failing tests before or with changes to governance semantics.
- Distinguish implemented behavior from target architecture in all public text.
- Do not weaken fail-closed behavior merely to accept malformed or incomplete
  policies.
- Update [`docs/PROJECT_STATUS.md`](docs/PROJECT_STATUS.md) after a material
  merge, design decision, milestone change, or newly discovered blocker.

## Context Management

- Use one chat or task per coherent outcome. Start a fresh task when the goal
  changes materially instead of carrying the entire project in one transcript.
- Keep the same chat while solving the same problem so relevant reasoning and
  decisions remain available.
- Treat `AGENTS.md`, `docs/PROJECT_STATUS.md`, committed code, tests, and Git
  history as durable context. Do not rely on chat memory for project truth.
- At the start of a fresh context, verify the working directory, Git branch,
  working tree, open pull requests, and CI before relying on a prior handoff.
- In Codex CLI, use `/status` to inspect remaining context and `/compact` when a
  long chat should continue with a concise summary of earlier turns.
- Use `/new` or `/clear` for a genuinely new outcome, `/fork` for an alternative
  approach, and `/resume` only when the original transcript remains relevant.
- Keep noisy exploration, long logs, and independent investigations out of the
  main thread when possible; return concise conclusions and file references.
- Before ending material work, update `docs/PROJECT_STATUS.md` with the verified
  state, decisions, validation results, blockers, and next recommended action.
- When this file changes, begin a new Codex session from the repository root so
  Codex rebuilds its instruction context from the updated guidance.

## Standard Verification

From the repository root:

```bash
python -m pip install -e .
python -m compileall -q src examples evals tests
agent-governance validate --strict
agent-governance policy validate examples/policies/multi_agent_operations.json
python -m unittest discover -s tests -v
```

For packaging changes, also build a wheel and smoke-test the installed CLI from
outside the repository.

## Fresh-Context Seed

Copy this into a new conversation when explicit kickoff context is useful:

> Continue development of the Agent Governance Harness repository. First read
> `AGENTS.md`, `docs/PRODUCT_CHARTER.md`, `docs/PRODUCT_SPEC.md`, `README.md`,
> `docs/PROJECT_STATUS.md`, `ROADMAP.md`, `docs/ARCHITECTURE.md`, and
> `docs/SAFETY_MODEL.md`. Then inspect the current
> Git branch and working tree, recent commits, open pull requests, and CI; do
> not rely on stale conversation state. Summarize the verified state before
> editing. Continue the highest-priority unblocked item in the project status,
> map material work to product-spec requirement IDs, apply the charter's
> anti-drift test, preserve the documented fail-closed and compatibility
> boundaries, run the relevant tests, and update `docs/PROJECT_STATUS.md`
> before handoff. Do not
> publish, merge, or delete remote work unless I explicitly ask.
