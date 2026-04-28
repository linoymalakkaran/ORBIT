# Instructions — Phase 07: Capability Fabric (Skills, Specs, Instructions)

> Add this file to your IDE's custom instructions when authoring or editing Capability Fabric content.

---

## Context

You are working on the **AD Ports Capability Fabric** — the shared knowledge layer of the AI Portal. The Fabric stores skills, specifications, instructions, and standards that encode AD Ports' organizational knowledge. Every AI agent reads the Fabric before generating code. Quality here directly determines quality of all generated output across the entire platform.

---

## Fabric Content Types

| Type | Format | Purpose | Examples |
|------|--------|---------|---------|
| Skill | Markdown | How-to guide for a specific pattern | `dotnet-cqrs-scaffold.md`, `playwright-e2e-baseline.md` |
| Specification | JSON Schema | Machine-readable contract | `adports-keycloak-realm.schema.json` |
| Instruction | Markdown | Policy document for AI tools | `coding-standards-csharp.md`, `security-baseline.md` |
| Standard | Markdown | External standard reference | `owasp-top10-adports.md` |

---

## Skill Document Requirements

Every skill document MUST have:

```markdown
# Skill: {Title}

## Skill ID                ← snake_case, unique across Fabric
## Version                 ← Semantic version: major.minor.patch
## Used By                 ← Which phases/agents use this skill
## Description             ← What this skill teaches the AI

## Skill Inputs            ← JSON schema of what the caller must provide
## Output Artefacts        ← What the skill produces (file tree)
## Step-by-Step Implementation  ← The actual content with code examples
## Acceptance Criteria     ← Testable criteria (AC1..ACN format)
## Common Mistakes         ← Table of pitfalls and fixes
```

## Specification Document Requirements

Every JSON Schema specification MUST:
- Include `$schema`, `$id`, `title`, `description`
- Include `additionalProperties: false` or `true` with documented reason
- Have `required` arrays at every nested level where fields are mandatory
- Include `examples` arrays for complex types
- Be validated with `ajv` or `jsonschema` before commit

## Instruction Document Requirements

Every instruction document MUST have:
- **Applies To** section (which services/phases/agents)
- **Forbidden Patterns** table (not just "do this" — also "never do this")
- **Owner** and **Next Review Date** (90-day cadence)

## Versioning Rules

```
Version MUST be bumped:
- patch (x.y.Z): Clarification, typo fix, example improvement
- minor (x.Y.0): New section, new example, additional rules
- major (X.0.0): Breaking change to pattern (forces agents to retrain)

OLD versions are NEVER deleted — they are archived with status: "archived"
```

## Quality Score Requirements

Before a skill is published to `status: active`, it must pass quality scoring:

| Check | Minimum |
|-------|---------|
| Has code examples | Yes (at least 1) |
| Has acceptance criteria | Yes (at least 3) |
| Has forbidden patterns | Yes (at least 2) |
| Has `Skill Inputs` JSON schema | Yes |
| Has `Output Artefacts` file tree | Yes |
| Word count (content sections) | ≥ 500 words |
| Related skills linked | ≥ 1 |

## Skills That Agents MUST Load

These skills are mandatory for the listed agents (agents fail pre-hook if not loaded):

| Agent | Mandatory Skills |
|-------|-----------------|
| Backend Specialist Agent | `dotnet-cqrs-scaffold`, `keycloak-realm-setup` |
| Frontend Specialist Agent | `angular-nx-microfrontend`, `keycloak-realm-setup` |
| QA Agent | `playwright-e2e-baseline`, `postman-newman-adports-baseline` |
| DevOps Agent | `dotnet-cqrs-scaffold`, `temporal-workflow-scaffold` |
| Fleet Upgrade Agent | `temporal-workflow-scaffold`, `framework-lifecycle-policy` |
| Hook Engine | `opa-rego-policy-authoring` |

## API Fabric Conventions

```http
GET  /api/fabric/skills                    → List all active skills
GET  /api/fabric/skills/{id}               → Get skill by ID (latest version)
GET  /api/fabric/skills/{id}/versions      → List all versions
GET  /api/fabric/skills/{id}/{version}     → Get specific version
GET  /api/fabric/skills/domain/{domain}    → Skills for a specific domain

GET  /api/fabric/specs                     → List all active specs
GET  /api/fabric/specs/{id}                → Get spec (returns JSON Schema)

GET  /api/fabric/instructions              → List all active instructions
GET  /api/fabric/instructions/{id}         → Get instruction document

GET  /api/fabric/search?q={query}          → Full-text search across all types
```

## Forbidden Patterns

| Pattern | Reason |
|---------|--------|
| Publishing a skill with no code examples | Agents cannot learn patterns from description alone |
| Deleting an old version | Agents referencing old versions in golden cases will break |
| Making breaking changes in a patch version | Version discipline enables safe agent upgrades |
| Hardcoding AD Ports-specific values in generic skills | Skills should be parameterised (use `{projectName}` placeholders) |
| Using `status: active` before passing quality check | Portal enforces quality gate on publish |

---

*Instructions — Phase 07 — AD Ports AI Portal — Applies to: Fabric Squad*
