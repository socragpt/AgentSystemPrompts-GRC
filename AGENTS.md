# Agent Working Agreement

This file routes coding agents to the context required for their task. Human
contributors can start with [`README.md`](README.md) and
[`CONTRIBUTING.md`](CONTRIBUTING.md).

## Start Every Fresh Context

1. Read [`docs/PRODUCT_CHARTER.md`](docs/PRODUCT_CHARTER.md) for the durable
   purpose, constitutional principles, boundaries, and anti-drift test.
2. Read [`README.md`](README.md) for the implemented product boundary and
   [`docs/PROJECT_STATUS.md`](docs/PROJECT_STATUS.md) for the verified current
   state and next priorities.
3. Inspect the current Git branch, working tree, remote, recent commits, open
   pull requests, and CI. Do not rely on prior chat or handoff state.
4. Select the additional context for the task from the routing table below.
5. Treat implementation and tests as authoritative when they disagree with a
   current-state document. Update the affected document in the same change.

## Task-Routed Context

| Task | Read before editing |
| --- | --- |
| Policy shape, validation, or compilation | [`docs/PRODUCT_SPEC.md`](docs/PRODUCT_SPEC.md), [`docs/SAFETY_MODEL.md`](docs/SAFETY_MODEL.md), [`docs/POLICY_BUNDLE_V0.1.md`](docs/POLICY_BUNDLE_V0.1.md), [`docs/ARCHITECTURE.md`](docs/ARCHITECTURE.md), and [`ROADMAP.md`](ROADMAP.md) |
| Action request, decision, reason code, or constraint | [`docs/PRODUCT_SPEC.md`](docs/PRODUCT_SPEC.md), [`docs/SAFETY_MODEL.md`](docs/SAFETY_MODEL.md), [`docs/DECISION_CONTRACT_V0.1.md`](docs/DECISION_CONTRACT_V0.1.md), [`docs/ARCHITECTURE.md`](docs/ARCHITECTURE.md), and [`ROADMAP.md`](ROADMAP.md) |
| Approval, enforcement, identity, evidence, or adapter behavior | Product Specification, Safety Model, both implemented contract documents, Architecture, and Roadmap |
| CLI, packaging, or CI | [`CONTRIBUTING.md`](CONTRIBUTING.md), `pyproject.toml`, `.github/workflows/ci.yml`, and each affected public document |
| Compatibility XML | `examples/legacy/SystemPrompt.xml`, `src/agent_governance/SystemPrompt.xml`, `src/agent_governance/prompt.py`, and the prompt and repository-contract tests |
| Documentation-only change | The document-authority map in [`docs/README.md`](docs/README.md), the source documents for each claim, and the implemented behavior that the text describes |
| Product direction or roadmap | Product Specification, Safety Model, Architecture, Roadmap, [`docs/BUSINESS_PURPOSE.md`](docs/BUSINESS_PURPOSE.md), and Project Status |

Read an entire selected document before acting on it. Do not load unrelated
reference, template, or research material unless the task requires it.

## Product Guardrails

- The project is a framework-neutral, policy-as-code governance harness for
  authority, delegation, approvals, constraints, and evidence requirements in
  multi-agent systems.
- The Product Charter is the stable authority for product purpose and
  boundaries. Architecture and implementation must conform to it.
- The current compiler emits deterministic policy artifacts. It does not
  authorize or dispatch runtime actions.
- The target product exposes one shared governance engine through a guided
  initializer, CLI, embedded SDK, decision service, and enforcement adapters.
  These surfaces must not develop different policy semantics.
- Missing, stale, ambiguous, or conflicting authority must fail closed.
- Delegation must not create authority that the delegator does not possess.
- The XML prompt is a compatibility path. Policy Bundle v0.1 is the structured
  path forward.
- Preserve the `agent_governance` Python import and `agent-governance` CLI
  unless a deliberate compatibility change is approved.
- Do not claim certification, legal compliance, or safety guarantees.

## Change Discipline

- Prefer one reviewable milestone per branch and pull request.
- Map material product work to requirement IDs in the Product Specification
  and run the Product Charter anti-drift test.
- Keep schemas, examples, documentation, tests, and compiled behavior aligned.
- Add precise failing tests before or with changes to governance semantics.
- Distinguish implemented behavior from target architecture in public text.
- Do not weaken fail-closed behavior to accept malformed or incomplete policy.
- Update Project Status after a material merge, design decision, milestone
  change, or newly discovered blocker.
- Do not publish, merge, delete remote work, or modify remote state unless the
  user explicitly authorizes it.

## Context and Handoff

- Use one task for one coherent outcome. Start a new task when the goal changes
  materially.
- Keep noisy exploration and independent investigations out of the main task
  when possible. Return concise conclusions and file references.
- Before ending material work, record verified state, decisions, validation
  results, blockers, and the next recommended action in Project Status.
- When this file changes, begin a new Codex task from the repository root so
  the updated instructions load into context.

## Standard Verification

Run the relevant subset during development. Run the complete baseline before a
material handoff:

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

For packaging changes, also build a wheel and smoke-test the installed CLI from
outside the repository.
