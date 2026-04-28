# Project Charter — AI Portal

## 1. Project Identity

| Field | Value |
|-------|-------|
| **Project Name** | AI Portal — Enterprise AI Orchestration Platform |
| **Version** | 1.0 |
| **Status** | Active |
| **Classification** | Internal / Confidential |
| **Organisation** | AD Ports Group — Technology Division |
| **Date** | April 2026 |

---

## 2. Problem Statement

AD Ports Group builds large, integration-heavy enterprise systems. Every new project repeats the same weeks of bootstrap work. After go-live, maintenance work — framework upgrades, security patches, library updates — has to be repeated separately in every project, consuming engineering capacity disproportionate to the business value delivered.

The core problem has three dimensions:
1. **Bootstrap waste** — 4–8 weeks of repeated setup per project (scaffolding, Keycloak, pipelines, infra, shared services).
2. **Maintenance fragmentation** — framework upgrades, security patches, and library updates applied independently in each of 40+ projects.
3. **Knowledge decay** — organisational standards and architectural patterns dissipate into tribal knowledge; each project re-learns them differently.

AI coding tools (Copilot, Cursor) have not fixed this — they accelerate keystrokes but have no access to AD Ports' standards, no portfolio view, and no maintenance capability.

---

## 3. Proposed Solution

The **AI Portal** is a centralized orchestration platform organized as a **capability fabric** — a shared layer of MCPs, agents, skills, specifications, and architectural standards that any AI tool can consume.

**Four value propositions:**
- **Generate** — BRD → approved architecture → running application in hours, not weeks.
- **Maintain** — fleet-wide upgrades, security patches, and library updates as coordinated campaigns.
- **Operate** — live health monitoring of every AD Ports service.
- **Govern** — every decision recorded in an immutable Pipeline Ledger.

---

## 4. Scope

### In Scope

| Category | Included |
|----------|----------|
| Project scaffolding | .NET CQRS + Angular MFE + Postgres + Keycloak + AKS |
| CI/CD pipelines | GitLab CI + Azure DevOps with SAST, SCA, quality gates |
| Infrastructure provisioning | AKS namespaces, Azure resources via Pulumi/Terraform |
| QA automation | Playwright E2E, k6 load, Axe accessibility, contract tests |
| Integration testing | Postman/Newman collections for deployed-system verification |
| BA/PM automation | User story generation for Jira and Azure DevOps |
| Ticket implementation | Auto-implementation of eligible Jira tickets |
| Security scanning | SonarQube, Checkmarx SAST, Snyk SCA, Trivy |
| Fleet operations | Campaign-based upgrade of entire project portfolio |
| Health monitoring | Live checks for all AD Ports services |
| Governance | Immutable Pipeline Ledger, hook engine, OpenFGA permissions |
| Ecosystem agents | MPay, Keycloak, CRM, Notification Hub, MDM, CMS, ERP, JUL, PCS |
| Legacy migration | Modernization mode for existing projects |
| Sovereign deployment | Air-gapped / on-premises option for classified workloads |

### Out of Scope

- Replacing Keycloak, AKS, PostgreSQL, or any existing production runtime.
- Building a proprietary DSL or new IDE.
- Building a low-code/no-code platform for business users.
- Replacing GitLab or Azure DevOps as VCS/CI platforms.
- AI training or fine-tuning (all LLMs consumed via API).

---

## 5. Success Criteria

The project is considered successful when:

1. **Gate 1 passed** — Portal takes a real BRD to a deployed, tested scaffold with full Pipeline Ledger trail.
2. **Gate 2 passed** — ≥5 pilot projects fully onboarded; Service Health Monitor active; PR Review ≥85% human-agreement.
3. **Gate 3 passed** — ≥50% of new projects start via Portal; first fleet campaign completed across ≥10 projects.
4. **Gate 4 passed** — External audit passed; sovereign deployment available; NESA compliance package delivered.

---

## 6. Stakeholders

| Role | Name | Responsibility |
|------|------|---------------|
| Executive Sponsor | CTO | Strategic direction, budget approval, Gate decisions |
| Product Owner | Head of Engineering | Phase scope, priority trade-offs |
| Technical Lead | Principal Architect | Architecture decisions, Gate 1 review |
| Platform Lead | Head of Platform Engineering | Skill/spec library ownership |
| Security Owner | Head of Information Security | Security baseline, NESA compliance |
| Compliance Owner | Internal Audit Lead | Pipeline Ledger requirements, audit sign-off |
| Delivery Lead | Engineering Manager | Sprint execution, team composition |
| Pilot Project Leads | TBD (3–5 tech leads) | Early adoption, feedback |

---

## 7. Governance Model

### Decision Authority

| Decision Type | Authority |
|--------------|-----------|
| Phase scope changes | Product Owner + Technical Lead |
| Gate go/no-go | CTO + Head of Engineering + Principal Architect |
| Technology substitutions | Principal Architect |
| LLM provider changes | Technical Lead + Security Owner |
| Production fleet campaigns (high-risk) | CTO + CAB |
| Shared Keycloak realm changes | Two architect sign-offs |

### Review Cadence

- **Daily standups** — per squad.
- **Weekly phase review** — per squad, 30 min, progress vs. plan.
- **Bi-weekly cross-squad sync** — Delivery Lead, all squad leads.
- **Gate review** — full stakeholder meeting, go/no-go decision, recorded in Pipeline Ledger.
- **Quarterly fabric review** — skills/specs/instructions review by Platform Lead + Principal Architect.

### Change Control

All scope changes go through the Product Owner. Changes above a declared complexity threshold require Gate adjustment. Emergency changes (zero-day CVE response) follow the emergency-override trail in the Hook Engine.

---

## 8. Budget Principles

| Category | Approach |
|----------|----------|
| LLM costs | Per-project budget hooks; portfolio-level cap; self-hosted fallback in Phase 4 |
| Cloud infrastructure | AKS cluster sized for Phase 1; auto-scaling enabled; reviewed at each Gate |
| Tooling licences | SonarQube, Checkmarx, LangSmith — enterprise licences negotiated before Phase 1 |
| Personnel | Squad model; external consultants for specialist gaps (LangGraph, Temporal.io) |
| Open-source | All integrate decisions are open-source or managed services; no proprietary agent runtimes |

---

## 9. Risk Summary

See [risk-register.md](risk-register.md) for the full register. Top five:

1. **Gate 1 failure** — orchestrator cannot produce reliable scaffolds → hard go/no-go at end of Phase 10+11.
2. **Adoption resistance** — teams don't switch → early-adopter programme, measurable wins published, Portal is optional first.
3. **Standards library rots** — skills/instructions drift from reality → quarterly review cadence enforced by tooling.
4. **LLM cost blowout** — unbounded agent spend → per-project budget hooks from Phase 18.
5. **Fleet campaign breaks projects** → wave-based rollout with pilot wave, auto-pause, one-click rollback.

---

## 10. Non-Negotiable Principles

1. **Developers keep their IDEs** — the Portal is additive, not a replacement.
2. **Determinism first, LLM second** — templates and rules for 70–80%; LLMs for 20–30%.
3. **Human-in-the-loop at every material gate** — Portal proposes; humans decide.
4. **Every action is recorded** — Pipeline Ledger is never optional.
5. **Build only what creates unique value** — integrate everything else from proven open-source.
6. **No proprietary runtime, no new DSL** — outputs are plain .NET + Angular + Helm.

---

*Project Charter v1.0 — AI Portal — April 2026*
