# CHANGELOG — AD Ports AI Portal Implementation Plan

All notable changes to this implementation plan document are recorded here.

Format follows [Keep a Changelog](https://keepachangelog.com/en/1.0.0/).

---

## [Unreleased]

### Planned
- External references for phases 03, 07, 08, 12, 13, 22, 24

---

## [2.3.0] — 2025-Q2

### Added
- `instructions.md` for all 25 phases (complete coverage)
- `external-refs.md` for phases 02, 05, 10, 15, 18, 25
- `shared/skills/keycloak-realm-setup.md` — Complete Keycloak provisioning skill
- `shared/skills/langgraph-agent-scaffold.md` — LangGraph agent template
- `shared/skills/opa-rego-policy-authoring.md` — OPA Rego policy patterns
- `shared/skills/temporal-workflow-scaffold.md` — Temporal workflow template
- `shared/prompts/brd-parser.md` — Stage 2 BRD parsing prompt
- `shared/prompts/work-package-decomposer.md` — Work package decomposition prompt
- `shared/prompts/story-generator.md` — User story generation prompt
- `shared/prompts/vulnerability-assessment.md` — CVE triage and assessment prompt
- `shared/prompts/health-runbook-generator.md` — Operational runbook generation prompt
- `shared/workflows/fleet-upgrade-campaign.md` — Fleet upgrade Temporal workflow
- `shared/workflows/ticket-implementation.md` — Ticket implementation LangGraph workflow
- `shared/workflows/vulnerability-remediation.md` — Vulnerability remediation workflow
- `shared/hooks/approval-gate-enforcement.rego` — Two-person rule and gate enforcement
- `shared/hooks/llm-tier-selection.rego` — LLM tier selection policies
- `shared/specs/adports-openapi-service.schema.json` — OpenAPI stub validation schema
- `shared/specs/adports-mcp-server.schema.json` — MCP server catalog schema
- `shared/specs/adports-argocd-app.schema.json` — ArgoCD Application validation schema
- `00-overview/glossary.md` — Portal-wide terminology definitions
- `CHANGELOG.md` — This file
- `CONTRIBUTING.md` — Contribution guidelines

---

## [2.2.0] — 2025-Q1

### Added
- Phase 21–25 phase documents (scale, sovereignty, domain packs)
- `shared/external-refs/external-references.md` — Consolidated external references
- `shared/instructions/framework-lifecycle-policy.md` — Framework version management

### Changed
- Phase 10 updated to reflect LangGraph 0.2+ StateGraph API
- Phase 15 updated to use ArgoCD 2.12

---

## [2.1.0] — 2024-Q4

### Added
- Phase 11–20 phase documents
- `shared/skills/playwright-e2e-baseline.md`
- `shared/skills/postman-newman-adports-baseline.md`
- `shared/hooks/budget-limits.rego`
- `shared/hooks/sensitive-data-redaction.rego`

### Changed
- Phase 03 updated to use .NET 9 (from .NET 8)
- Technology stack updated: Angular 20, PrimeNG 18

---

## [2.0.0] — 2024-Q3

### Added
- Complete 25-phase implementation plan structure
- `00-overview/` directory: project-charter, technology-stack, team-structure, success-metrics, risk-register
- Phase 01–10 phase documents with full detail
- `shared/instructions/coding-standards-csharp.md`
- `shared/instructions/coding-standards-angular.md`
- `shared/instructions/security-baseline.md`
- `shared/skills/dotnet-cqrs-scaffold.md`
- `shared/skills/angular-nx-microfrontend.md`
- `shared/hooks/role-based-provisioning.rego`
- `shared/hooks/forbidden-operations.rego`
- `shared/prompts/intent-extraction.md`
- `shared/prompts/architecture-proposal.md`
- `shared/prompts/pr-review-rubric.md`
- `shared/specs/adports-keycloak-realm.schema.json`
- `shared/specs/adports-helm-chart.values.schema.json`
- Phase 01 `instructions.md` and `external-refs.md`
- Phase 02, 04, 10 `instructions.md`

### Breaking Changes
- Implementation plan restructured from v1 flat structure to v2 hierarchical structure

---

## [1.0.0] — 2024-Q1

### Added
- Initial v1 implementation plan (flat Markdown documents)
- Basic phase descriptions for phases 1–15

---

*CHANGELOG — AD Ports AI Portal Implementation Plan*
