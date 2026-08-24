# Key Terms

This glossary gives the repository a shared vocabulary for governance, risk,
compliance, and agentic systems. Some terms describe the target architecture
and do not imply that the capability is implemented in the current alpha.

## Agent

A software actor that proposes or performs actions under authority delegated
by a principal.

## Approval

An authorization by an eligible principal or service for an exact action,
scope, and set of constraints.

## Approval Grant

A versioned record binding individual approver decisions to one exact request,
unresolved policy decision, effective scope, and expiry. Approval Grant v0.1 is
single-use and requires explicit caller-supplied revocation and reuse state.

## Approval Verification Result

A separate `satisfied` or `not_satisfied` result stating whether an exact grant
meets an unresolved `require_approval` decision under supplied verification
state. It does not change the decision to `allow` or authorize dispatch.

## Assumption

A belief or statement accepted as true without proof and used as a premise for
reasoning or decision-making.

## Audit

A systematic review of financial or operational activities against defined
criteria to assess accuracy, integrity, or compliance.

## Authority

A bounded grant to perform specified actions over specified resources under
stated constraints.

## Benchmark

A standard reference point used to measure performance or progress toward a
goal.

## Budget

A defined limit or allocation for money, time, actions, or other resources.

## Capability

A technical means by which an agent can affect a resource, call a tool, or
communicate with another actor.

## Channel

A defined path for messages or actions with known participants, permitted data
types, and applicable controls.

## Charter

A formal document that defines the scope, objectives, guidelines, and
responsibilities of a project or group of agents.

## Compliance

Conformance with applicable laws, regulations, policies, and standards.
Evidence may support a compliance assessment but does not by itself establish
or certify compliance.

## Constraint

A limitation or condition that bounds an action, decision, resource, or
delegation.

## Context

The circumstances and background that shape the interpretation of an event,
instruction, or decision.

## Control

A policy-backed rule or mechanism intended to prevent, detect, constrain, or
record risk-relevant behavior.

## Data

Facts, records, or observations used for analysis and decision-making. Data
does not have instructional authority unless an authorized policy grants it.

## Decision

A policy evaluation result. Decision Contract v0.1 returns exactly `allow`,
`deny`, or `require_approval`; enforcement of that result remains a separate
boundary.

## Delegation

The bounded assignment of existing authority from one actor to another. A
delegation cannot create authority the delegating actor does not possess.

## Evidence Record

A structured record connecting a proposed action and outcome to the actor,
authority, policy version, applicable controls, approvals, and execution
result.

## Expectation

A defined standard or anticipated outcome for a process or agent.

## Fallacy

An error in reasoning that can produce an unsound conclusion or decision.

## Focus

Concentrated attention on priority outcomes, exclusions, and tradeoffs.

## Goal

A desired result or milestone that guides strategic and operational efforts.

## Governance Harness

The external system of policies, permissions, decision points, communication
boundaries, monitors, and evidence mechanisms surrounding one or more agents.

## GRC

Governance, Risk, and Compliance: an integrated approach to managing
objectives, uncertainty, obligations, and accountability.

## Impact

The effect an action or event has on objectives, resources, or stakeholders.

## Least Privilege

The principle that an actor receives only the capabilities and access needed
for an authorized purpose, for no longer than required.

## Minutes

Written records summarizing discussions, decisions, and action items from a
meeting.

## Monitor

A component or role that observes decisions, actions, evidence, or outcomes
and reports deviations from approved expectations.

## Objective

A clear, measurable step toward achieving a goal.

## Output

The tangible product, report, record, or deliverable produced by a process.

## Plan

A structured outline of authorized actions and resources for reaching an
objective.

## Policy

A formal rule or set of rules governing consistent decisions and actions.

## Policy Bundle

A versioned, structured collection of governance entities, relationships,
controls, provenance, and lifecycle metadata intended for validation and
compilation.

## Principal

An authenticated person, service, or organization that originates, holds, or
delegates authority.

## Procedure

Detailed steps describing how to perform a specific task or process.

## Process

A series of actions or operations leading to a result.

## Product

A good or service generated to meet a need or solve a problem.

## Prompt

An input that requests or shapes a model response. A prompt is not, by itself,
proof of authority or enforcement.

## Requirement

A condition or capability that must be satisfied.

## Resource

Data, systems, funds, time, credentials, people, or materials used to perform
an action.

## Responsibility

The obligation to perform assigned duties and be answerable for outcomes.

## Risk

The possibility that uncertainty, action, or inaction will adversely affect
objectives or stakeholders.

## Role

A named set of responsibilities and bounded permissions assignable to an
actor.

## Stakeholder

An individual or group that has an interest in or is affected by an
organization's activities.

## Standard

An agreed requirement or benchmark for quality, performance, or conformance.

## Strategy

A long-term approach that aligns resources and actions with goals.

## Tactic

A specific, shorter-term method used to execute a strategy.

## Tool

An external capability through which an agent can read data, communicate, or
change state.

## Value

The benefit or importance derived from a product, service, decision, or
action.
