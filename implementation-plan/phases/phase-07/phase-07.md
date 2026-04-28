# Phase 07 — Capability Fabric (Skills, Specs, Instructions)

## Summary

Build the **Capability Fabric** — the shared library of skills, specifications, and instructions that encode AD Ports' organizational knowledge. This is the content that makes the AI Portal intelligent about AD Ports' specific stack, patterns, and standards. The fabric is consumed by the Portal's own Orchestrator **and** by external tools (Copilot, Cursor, Claude Code) via MCP.

---

## Objectives

1. Define the skill/spec/instruction schema and versioning model.
2. Implement the Fabric API (CRUD for skills, specs, instructions with versioning).
3. Author the initial AD Ports skill library (minimum 15 foundational skills).
4. Author the initial specification library (8 machine-readable contracts).
5. Author the initial instruction library (10 policy documents).
6. Implement the AD Ports Standards MCP server (query fabric from any IDE).
7. Implement the Fabric Admin UI in the Portal (author, review, publish skills).
8. Implement skill quality scoring (completeness, testability, coverage checks).
9. Wire skill versioning to Framework Lifecycle Policy.
10. Implement scheduled review cadence enforcement.

---

## Prerequisites

- Phase 03 (Portal Backend API — Admin API stubs).
- Phase 04 (Portal UI — Admin section stub).
- Phase 02 (Auth and data layer).

---

## Duration

**3 weeks**

**Squad:** Fabric Squad (1 principal architect + 1 senior .NET + 1 Python + 1 technical writer)

---

## Deliverables

| # | Deliverable | Acceptance Criterion |
|---|------------|---------------------|
| D1 | Fabric schema + API | CRUD with versioning; `GET /api/fabric/skills` returns list |
| D2 | Skill library (15 skills) | All skills parseable; validated against schema |
| D3 | Spec library (8 specs) | All specs valid JSON Schema / OpenAPI |
| D4 | Instruction library (10 docs) | All instructions have owner, version, next-review date |
| D5 | AD Ports Standards MCP server | `fetch-coding-standard`, `list-approved-libraries`, `get-naming-conventions` tools work |
| D6 | Fabric Admin UI | Author/publish a skill; flag stale review |
| D7 | Skill quality scorer | Scores completeness, coverage, testability |
| D8 | Scheduled review cadence | Overdue skills flagged in Portal dashboard |
| D9 | Fabric versioning | Each skill version is immutable; new versions are new entries |
| D10 | Evaluation harness connector | Orchestrator can pull skills in Phase 10 |

---

## Fabric Schema

### Skill Document

```json
{
  "$schema": "https://schemas.adports.ae/ai-portal/skill/v1.json",
  "id": "dotnet-cqrs-scaffold",
  "version": "1.2.0",
  "title": "AD Ports .NET CQRS Scaffold",
  "description": "How to scaffold a .NET 9 CQRS microservice following AD Ports conventions",
  "tags": ["dotnet", "cqrs", "backend", "scaffold"],
  "technology_stack": ["dotnet-9", "efcore", "mediatr", "fluentvalidation"],
  "owner": "platform-engineering",
  "last_reviewed": "2026-01-15",
  "next_review": "2026-04-15",
  "review_cadence_days": 90,
  "status": "active",
  "sections": [
    {
      "id": "project-structure",
      "title": "Project Structure",
      "content": "..."
    },
    {
      "id": "cqrs-pattern",
      "title": "CQRS Pattern",
      "content": "..."
    }
  ],
  "examples": [
    { "title": "CreateOrderCommand", "language": "csharp", "code": "..." }
  ],
  "related_skills": ["keycloak-realm-setup", "dotnet-efcore-migrations"],
  "related_specs": ["adports-dotnet-project-structure.schema.json"],
  "related_instructions": ["coding-standards-csharp.md"]
}
```

### Specification Document

```json
{
  "$schema": "https://schemas.adports.ae/ai-portal/spec/v1.json",
  "id": "adports-keycloak-realm",
  "version": "2.1.0",
  "title": "AD Ports Keycloak Realm Configuration",
  "description": "Standard realm configuration for AD Ports applications",
  "schema_type": "json-schema",
  "schema": { ... },  // JSON Schema or OpenAPI spec inline
  "owner": "identity-team",
  "last_reviewed": "2026-02-01",
  "next_review": "2026-05-01"
}
```

### Instruction Document

```markdown
---
id: coding-standards-csharp
version: 3.0.0
title: AD Ports C# Coding Standards
owner: platform-engineering
last_reviewed: 2026-01-10
next_review: 2026-04-10
review_cadence_days: 90
applies_to: [dotnet-9, dotnet-8]
---

# AD Ports C# Coding Standards

## Naming Conventions
...
```

---

## Initial Skill Library (15 Skills to Author)

| ID | Title | Priority |
|----|-------|---------|
| `dotnet-cqrs-scaffold` | .NET 9 CQRS Microservice Scaffold | Critical |
| `keycloak-realm-setup` | Keycloak Realm Configuration | Critical |
| `angular-nx-microfrontend` | Angular Nx MFE with Native Federation | Critical |
| `dotnet-efcore-migrations` | EF Core + DbUp Migration Pattern | High |
| `playwright-e2e-baseline` | AD Ports Playwright E2E Framework | High |
| `postman-newman-adports-baseline` | Postman/Newman Integration Test Baseline | High |
| `docker-helm-aks-baseline` | Docker + Helm Chart + AKS Deployment | High |
| `gitlab-ci-secure-pipeline` | GitLab CI Pipeline with SAST/SCA | High |
| `azure-devops-secure-pipeline` | Azure DevOps Pipeline with SAST/SCA | High |
| `rabbitmq-masstransit-pattern` | RabbitMQ + MassTransit Integration | Medium |
| `pulumi-azure-infrastructure` | Pulumi Azure Infrastructure Patterns | Medium |
| `opentelemetry-dotnet` | OpenTelemetry Setup for .NET Services | Medium |
| `fleet-upgrade-playbook-dotnet` | .NET Framework Upgrade Fleet Playbook | Medium |
| `health-check-baseline` | Service Health Check Configuration | Medium |
| `sonarqube-checkmarx-quality-gate` | SonarQube + Checkmarx Quality Gates | Medium |

---

## Initial Specification Library (8 Specs)

| ID | Format | Purpose |
|----|--------|---------|
| `adports-keycloak-realm.schema.json` | JSON Schema | Standard Keycloak realm config |
| `adports-helm-chart.values.schema.json` | JSON Schema | Helm chart values validation |
| `adports-dotnet-project-structure.schema.json` | JSON Schema | .NET project folder structure |
| `mpay-integration.openapi.yaml` | OpenAPI 3.1 | MPay payment API contract |
| `adports-angular-nx.schema.json` | JSON Schema | Nx workspace configuration |
| `adports-pipeline-variables.schema.json` | JSON Schema | Required CI/CD variables |
| `adports-health-check.schema.json` | JSON Schema | Health probe configuration |
| `adports-ledger-event.schema.json` | JSON Schema | Pipeline Ledger event envelope |

---

## Initial Instruction Library (10 Docs)

| ID | Title | Applies To |
|----|-------|-----------|
| `coding-standards-csharp` | C# Coding Standards | All .NET projects |
| `coding-standards-angular` | Angular/TypeScript Standards | All frontend projects |
| `security-baseline` | Security Baseline for All Projects | All projects |
| `framework-lifecycle-policy` | Framework Version Lifecycle Policy | All projects |
| `fleet-campaign-policy` | Fleet Campaign Rules & Risk Tiers | Fleet operations |
| `health-monitoring-policy` | Service Health Monitoring Policy | All services |
| `data-residency-policy` | Data Residency & LLM Routing Policy | All AI operations |
| `pr-review-standards` | Pull Request Quality Standards | All PRs |
| `api-design-standards` | REST API Design Standards | All API services |
| `secret-management-policy` | Secret Handling & Rotation Policy | All services |

---

## AD Ports Standards MCP Server

```python
# Implemented as a FastAPI + MCP SDK server
from mcp import McpServer, Tool

server = McpServer("adports-standards")

@server.tool("fetch_coding_standard")
async def fetch_coding_standard(language: str, topic: str | None = None) -> str:
    """Fetch AD Ports coding standard for a specific language and optional topic."""
    instruction = await fabric_service.get_instruction(f"coding-standards-{language}")
    if topic:
        return instruction.get_section(topic)
    return instruction.full_content

@server.tool("list_approved_libraries")
async def list_approved_libraries(stack: str, category: str | None = None) -> list[dict]:
    """List AD Ports approved libraries for a given technology stack."""
    spec = await fabric_service.get_spec("adports-approved-libraries")
    return spec.filter(stack=stack, category=category)

@server.tool("get_naming_conventions")
async def get_naming_conventions(context: str) -> dict:
    """Get AD Ports naming conventions for a given context (dotnet, angular, database, etc.)."""
    instruction = await fabric_service.get_instruction("coding-standards-csharp")
    return instruction.get_section("naming-conventions")

@server.tool("get_skill")
async def get_skill(skill_id: str, section: str | None = None) -> str:
    """Retrieve an AD Ports skill document or a specific section."""
    skill = await fabric_service.get_skill(skill_id)
    if section:
        return skill.get_section(section)
    return skill.full_content

@server.tool("list_skills")
async def list_skills(tags: list[str] | None = None, stack: str | None = None) -> list[dict]:
    """List available AD Ports skills, optionally filtered by tags or stack."""
    return await fabric_service.list_skills(tags=tags, stack=stack)
```

---

## Step-by-Step Execution Plan

### Week 1: Schema + API + Initial Content

- [ ] Define and validate skill, spec, instruction schemas.
- [ ] Implement Fabric API (CRUD, versioning, search by tags/stack).
- [ ] Author `dotnet-cqrs-scaffold` skill (this is the most critical one; review with principal architect).
- [ ] Author `keycloak-realm-setup` skill.
- [ ] Author `coding-standards-csharp` instruction.
- [ ] Author `adports-keycloak-realm.schema.json` spec.

### Week 2: Remaining Content + MCP Server

- [ ] Author remaining 13 skills (see priority list).
- [ ] Author remaining 7 specs and 9 instructions.
- [ ] Implement AD Ports Standards MCP server (Python + FastAPI + MCP SDK).
- [ ] Deploy MCP server to AKS.
- [ ] Test: `@adports-standards get_skill dotnet-cqrs-scaffold` from Cursor returns content.

### Week 3: Admin UI + Quality + Cadence

- [ ] Implement Fabric Admin UI (list, create, edit, publish, deprecate).
- [ ] Implement skill quality scorer (checks: has examples, has related specs, has owner, review date set).
- [ ] Implement review cadence enforcement (background worker flags overdue items).
- [ ] Portal dashboard: "3 skills overdue for review" banner.
- [ ] Write evaluation harness connector (Orchestrator can fetch skills in Phase 10).

---

## Gate Criterion

- All 15 skills, 8 specs, 10 instructions authored and published.
- AD Ports Standards MCP server responds to all 5 tools from Copilot/Cursor.
- Skill quality scorer runs on all skills; all score ≥70/100.
- Review cadence enforcement: intentionally overdue skill appears in Portal dashboard.
- `GET /api/fabric/skills?tags=dotnet` returns correct subset.

---

*Phase 07 — Capability Fabric — AI Portal — v1.0*
