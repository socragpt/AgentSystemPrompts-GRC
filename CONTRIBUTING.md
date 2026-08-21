# Contributing

Contributions should make the harness more explicit, testable, and enforceable.

## Development Setup

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
python -m pip install -e .
python -m unittest discover -v
```

## Pull Requests

1. Keep each pull request focused on one governance or engineering outcome.
2. Explain the context, objective, assumptions, risks, and compatibility impact.
3. Add tests for executable behavior and examples for new public interfaces.
4. Identify any safety invariant or policy-precedence behavior affected by the change.
5. Update the README or roadmap when implemented capability changes.

Normative requirements use **MUST**, **MUST NOT**, **SHOULD**, and **MAY** deliberately. Avoid describing an aspirational feature as implemented.

## Policy Changes

Changes to `examples/legacy/SystemPrompt.xml` or the packaged copy in
`src/agent_governance/SystemPrompt.xml` must receive the same review as code.
A policy change should state its owner, intended effect, failure mode, and how
the behavior can be evaluated. The repository contract test requires those two
compatibility copies to remain byte-identical.
