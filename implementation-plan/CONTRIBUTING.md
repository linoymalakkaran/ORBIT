# Contributing to the AD Ports AI Portal Implementation Plan

> This guide explains how to contribute to the implementation plan — adding phases, skills, prompts, specs, hooks, and workflows.

---

## Who Can Contribute?

| Contribution Type | Who Can Author | Who Reviews |
|------------------|---------------|-------------|
| New phase document | Any squad lead | Delivery Lead + Architect |
| New skill | Any developer | Fabric Squad lead |
| New prompt | Any agent developer | Governance Squad |
| New Rego policy (hook) | Governance Squad only | Minimum 2 Governance reviewers |
| New JSON Schema spec | Any squad lead | Fabric Squad lead |
| New workflow | Platform Squad | Architect + Governance Squad |
| Edits to coding standards | Squad lead | Delivery Lead (sign-off required) |

---

## Directory Structure

```
implementation-plan/
├── README.md
├── CHANGELOG.md
├── CONTRIBUTING.md              ← This file
├── 00-overview/
│   ├── project-charter.md
│   ├── technology-stack.md
│   ├── team-structure.md
│   ├── success-metrics.md
│   ├── risk-register.md
│   └── glossary.md
├── phases/
│   └── phase-{NN}/
│       ├── phase-{NN}.md        ← Phase specification
│       ├── instructions.md      ← IDE agent instructions
│       └── external-refs.md    ← External documentation links
└── shared/
    ├── instructions/            ← Coding standards, policies
    ├── skills/                  ← How-to guides for AI agents
    ├── hooks/                   ← OPA Rego policy files
    ├── prompts/                 ← LLM prompt templates
    ├── workflows/               ← Orchestration workflow blueprints
    ├── specs/                   ← JSON Schema validation files
    └── external-refs/           ← Consolidated external references
```

---

## Adding a New Phase

1. Create the directory: `phases/phase-{NN}/`
2. Create `phase-{NN}.md` using the template below:

```markdown
# Phase {NN}: {Title}

## Overview
## Goals
## Prerequisites
## Deliverables
## Acceptance Criteria
## Timeline
## Squad Assignments
```

3. Create `instructions.md` — IDE agent guidance for this phase
4. Create `external-refs.md` — external documentation links
5. Update `README.md` phase table
6. Update `CHANGELOG.md` under `[Unreleased]`
7. Submit MR with label: `plan-update`, `phase-document`

---

## Adding a New Skill

Skills encode "how to do X" for AI agents. Every skill must:

1. Be placed in `shared/skills/{skill-id}.md`
2. Follow the required structure (see `phase-07/instructions.md` for quality requirements)
3. Have a Skill ID in snake_case
4. Pass the quality score (6 checks — see Phase 07 instructions)
5. Be listed in the appropriate agent's mandatory skills table

Skill ID naming convention: `{domain}-{action}-{target}`
Examples: `dotnet-cqrs-scaffold`, `keycloak-realm-setup`, `playwright-e2e-baseline`

---

## Adding a New Prompt

Prompts are LLM prompt templates for specific orchestration tasks.

1. Place in `shared/prompts/{prompt-name}.md`
2. Include: purpose, input schema, output schema, example I/O, forbidden outputs
3. All prompts must produce **structured JSON output** — no free-form text
4. Include at least one complete worked example with realistic AD Ports data

---

## Adding a New OPA Policy (Hook)

**Note: Hook Engine policies require Governance Squad authorship.**

1. Place in `shared/hooks/{policy-name}.rego`
2. Package: `adports.hooks.{policy_name}`
3. Always start with: `default allow := false`
4. Create `{policy-name}_test.rego` with ≥ 3 allow + ≥ 3 deny test cases
5. Run `opa test shared/hooks/ -v` — all tests must pass
6. Add policy to `shared/hooks/README.md` policy index
7. Submit MR with labels: `policy-change`, `governance-review`
8. Requires 2 Governance Squad reviewer approvals

---

## Adding a New JSON Schema Spec

1. Place in `shared/specs/adports-{entity}.schema.json`
2. Must include: `$schema`, `$id`, `title`, `description`
3. Use `$id` format: `https://schemas.adports.ae/ai-portal/{entity}.schema.json`
4. Include `additionalProperties: false` (or document why `true`)
5. Test with: `npx ajv validate -s shared/specs/{file} -d examples/valid-example.json`

---

## Adding a New Workflow

Workflows document orchestration patterns for AI agents.

1. Place in `shared/workflows/{workflow-name}.md`
2. Include: purpose, trigger, Temporal vs LangGraph decision, state definition, nodes/activities, signal handlers, error handling, example run
3. All state fields must be typed (Python TypedDict)
4. Include a Mermaid state diagram

---

## Pull Request Guidelines

- **MR title format**: `[{Phase}] Brief description of change`
- **MR description**: What changed, why, what was tested
- **Labels**: Add at least one content-type label:
  - `phase-document`, `skill`, `prompt`, `policy-change`, `spec`, `workflow`, `bug-fix`
- **Branch naming**: `docs/{phase-or-area}/{short-description}`
- **Review requirements**: At least 1 reviewer from the relevant squad

---

## Versioning

When modifying existing content:
- **Patch** (x.y.Z): Clarifications, typo fixes, link updates — no version bump needed
- **Minor** (x.Y.0): New section, new examples, new acceptance criteria — bump version in file
- **Major** (X.0.0): Breaking pattern change — requires Delivery Lead approval

---

## Code of Conduct

- Respect AD Ports information classification — no real customer data in examples
- All contributed content becomes intellectual property of AD Ports Group
- Contributors are responsible for ensuring no third-party IP violations

---

*CONTRIBUTING.md — AD Ports AI Portal Implementation Plan*
