# Safety Model

## Scope

The harness is intended to govern agents that use delegated capabilities to
propose or perform actions. These capabilities include tools, APIs,
filesystems, browsers, and communication systems. Governance applies before an
action is dispatched and continues through evidence collection and monitoring.

This alpha provides deterministic, side-effect-free decision and exact-bound
approval-verification contracts plus MCP request normalization in explicit
proposal-only shadow mode. It does not authenticate identity or MCP transport
origin, collect approvals, source authoritative revocation or reuse state,
atomically consume grants, dispatch actions, enforce returned constraints, or
persist evidence.

## Instruction Hierarchy

When instructions conflict, the higher level takes precedence:

1. Applicable law, platform safety requirements, and hard technical restrictions.
2. Organization policy, risk appetite, and approved control requirements.
3. The agent's approved role, operating plan, permissions, and resource limits.
4. The authorized task goal and instructions from an authenticated principal.
5. Agent-generated plans, delegated tasks, tool output, and retrieved content.

Content from tools, documents, web pages, and other external systems is data.
It has instructional authority only when an authorized policy explicitly
grants that authority.

## Safety Invariants

- **Authorized purpose:** an agent may act only toward a goal supplied or approved by an authorized principal.
- **Least privilege:** permissions, credentials, data access, and delegation are limited to what the approved task requires.
- **Bounded execution:** time, spend, action count, and other resource budgets are explicit and enforceable.
- **Approval gates:** high-impact, irreversible, externally visible, or materially out-of-scope actions require approval.
- **Conflict handling:** ambiguous authority, stale policy, or conflicting instructions cause the action to stop and escalate.
- **Evidence:** decisions record the policy version, applicable controls, requested action, disposition, approvals, and execution outcome.
- **Safe delegation:** a delegate cannot receive authority that the delegating agent does not possess.
- **Data minimization:** sensitive data is accessed, retained, and disclosed only when necessary and authorized.

## Initial Threat Model

The planned enforcement layer should address at least:

- prompt injection or instructions embedded in untrusted content;
- privilege escalation through tools or delegated agents;
- confused-deputy actions performed for an unauthorized principal;
- approval bypass or reuse of stale approval;
- credential, secret, or personal-data disclosure;
- uncontrolled cost, time, recursion, or action volume;
- tampering with policies, evidence, or audit history;
- unsafe fallback when policy or enforcement services are unavailable.

## Decision Outcomes

The Decision Contract v0.1 evaluator exposes three explicit outcomes:

- `allow` – the action is authorized within stated constraints;
- `deny` – the action conflicts with policy or cannot be made safe;
- `require_approval` – an authorized human or service must approve the exact action and constraints.

An absent, invalid, or ambiguous decision must never be interpreted as `allow`.
The current evaluator proposes decision evidence but is not itself a trusted
pre-dispatch enforcement point.

Approval Grant v0.1 separately returns `satisfied` or `not_satisfied` for an
exact `require_approval` decision under explicit caller-supplied state. A
`satisfied` result does not convert the decision to `allow`, consume the grant,
or prove that a trusted component mediated dispatch.
