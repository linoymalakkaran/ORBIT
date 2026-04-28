# AI Portal — Implementation Plan

> **One portal. All agents. Every standard. Forever maintained.**

This folder contains the complete, phased implementation plan for the **AD Ports AI Portal** — an enterprise AI orchestration platform that turns business documents into production-ready, standards-compliant software.

---

## Document Map

```
implementation-plan/
├── README.md                        ← You are here — master index & navigation
│
├── 00-overview/
│   ├── project-charter.md           ← Scope, goals, stakeholders, governance
│   ├── technology-stack.md          ← Full build-vs-integrate decisions
│   ├── team-structure.md            ← Squad model, roles, responsibilities
│   ├── success-metrics.md           ← KPIs per phase
│   └── risk-register.md             ← All risks with mitigations
│
├── phases/
│   ├── phase-01/  Platform Foundation & Infrastructure
│   ├── phase-02/  Core Data Layer & Identity
│   ├── phase-03/  Portal Backend API (CQRS .NET)
│   ├── phase-04/  Portal Frontend UI (Angular)
│   ├── phase-05/  Pipeline Ledger (Immutable Audit)
│   ├── phase-06/  Shared Project Context (Redis)
│   ├── phase-07/  Capability Fabric — Skills, Specs, Instructions
│   ├── phase-08/  MCP Server Foundation
│   ├── phase-09/  Additional MCP Servers (9 servers)
│   ├── phase-10/  Orchestration Agent Core
│   ├── phase-11/  Architecture Proposal & Review Workflow
│   ├── phase-12/  Backend Specialist Agent
│   ├── phase-13/  Frontend Specialist Agent
│   ├── phase-14/  Database & Integration Agents
│   ├── phase-15/  DevOps & Infrastructure Agents
│   ├── phase-16/  QA Automation Agent
│   ├── phase-17/  Integration Test Agent (Postman/Newman)
│   ├── phase-18/  Hook Engine & Guardrails
│   ├── phase-19/  Project Registry & Component Reuse
│   ├── phase-20/  Service Health Monitor
│   ├── phase-21/  PR Review Agent & Code Quality Gate
│   ├── phase-22/  BA/PM Story Agent & Ticket Implementation
│   ├── phase-23/  Vulnerability Radar & Framework Obsolescence Monitor
│   ├── phase-24/  Fleet Upgrade & Framework Migration Agent
│   └── phase-25/  Ecosystem Agents, Scale & Sovereignty
│
└── shared/
    ├── instructions/                ← Global AI coding instructions
    ├── skills/                      ← Reusable skill packages
    ├── specs/                       ← Machine-readable contracts
    ├── hooks/                       ← OPA/Rego policy hooks
    ├── prompts/                     ← AI agent prompt templates
    ├── workflows/                   ← Temporal/LangGraph workflow definitions
    └── external-refs/               ← External documentation references
```

---

## Phase Overview & Timeline

| Phase | Name | Whitepaper Gate | Duration | Depends On |
|-------|------|----------------|----------|------------|
| 01 | Platform Foundation & Infrastructure | Pre-Gate 1 | 3 weeks | — |
| 02 | Core Data Layer & Identity | Pre-Gate 1 | 2 weeks | 01 |
| 03 | Portal Backend API | Pre-Gate 1 | 3 weeks | 02 |
| 04 | Portal Frontend UI | Pre-Gate 1 | 3 weeks | 03 |
| 05 | Pipeline Ledger | Pre-Gate 1 | 2 weeks | 02, 03 |
| 06 | Shared Project Context | Pre-Gate 1 | 2 weeks | 02, 05 |
| 07 | Capability Fabric | Gate 1 | 3 weeks | 03 |
| 08 | MCP Server Foundation | Gate 1 | 2 weeks | 07 |
| 09 | Additional MCP Servers | Gate 1 | 3 weeks | 08 |
| 10 | Orchestration Agent Core | **Gate 1** | 4 weeks | 06, 07, 08 |
| 11 | Architecture Proposal & Review Workflow | Gate 1 | 3 weeks | 10 |
| 12 | Backend Specialist Agent | Gate 1 | 3 weeks | 10, 11 |
| 13 | Frontend Specialist Agent | Gate 1 | 3 weeks | 10, 11 |
| 14 | Database & Integration Agents | Gate 1 | 2 weeks | 10 |
| 15 | DevOps & Infrastructure Agents | Gate 1 | 3 weeks | 09, 12 |
| 16 | QA Automation Agent | Gate 2 | 3 weeks | 12, 13 |
| 17 | Integration Test Agent | Gate 2 | 2 weeks | 15, 16 |
| 18 | Hook Engine & Guardrails | Gate 2 | 2 weeks | 03, 10 |
| 19 | Project Registry | Gate 2 | 2 weeks | 03, 10 |
| 20 | Service Health Monitor | **Gate 2** | 3 weeks | 09, 18, 19 |
| 21 | PR Review Agent | Gate 3 | 3 weeks | 12, 18 |
| 22 | BA/PM Story Agent & Ticket Impl | Gate 3 | 3 weeks | 09, 10 |
| 23 | Vulnerability Radar & Obsolescence Monitor | Gate 3 | 2 weeks | 19, 18 |
| 24 | Fleet Upgrade & Framework Migration | **Gate 3** | 4 weeks | 19, 23, 15 |
| 25 | Ecosystem Agents, Scale & Sovereignty | Gate 4 | 6 weeks | All previous |

**Total estimated duration (sequential):** ~72 weeks  
**Parallel execution available:** Phases 3+4 run in parallel; phases 12+13+14 run in parallel; phases 16+17+18+19 run in parallel.  
**Realistic calendar time with 3 squads:** ~28–32 weeks to Gate 1, ~52–56 weeks to Gate 4.

---

## The Four Gates

### Gate 1 — Foundation (end of Phase 15)
> Given a real AD Ports BRD, the Portal produces a reviewed, approved architecture and scaffolds a working application passing build, test, security scan, and initial AKS deployment. Pipeline Ledger records every stage. Shared project context works across multiple team members.

**Go/No-Go decision required before Phase 16.**

### Gate 2 — Ecosystem & Workflow (end of Phase 20)
> Pilot projects onboarded. PR review agent achieves ≥85% human-agreement. Service Health Monitor active. BA story quality acceptable. All shared services wired automatically.

**Go/No-Go decision required before Phase 21.**

### Gate 3 — Intelligence & Fleet (end of Phase 24)
> Majority of new projects start via Portal. First successful fleet campaign completed. Ticket Implementation Agent at acceptable merge rate. Vulnerability radar producing auto-PRs.

**Go/No-Go decision required before Phase 25.**

### Gate 4 — Scale & Sovereignty (end of Phase 25)
> External audit passed. Fleet campaigns at portfolio scale. Sovereign deployment available. NESA compliance package delivered.

---

## Squad Model

| Squad | Phases | Responsibilities |
|-------|--------|----------------|
| **Infra Squad** | 01, 02 | AKS, Postgres, Redis, Kafka, Vault, monitoring |
| **Core Squad** | 03, 04, 05, 06 | Portal backend, Portal UI, Ledger, Context |
| **Fabric Squad** | 07, 08, 09 | Skills, Specs, Instructions, MCP servers |
| **Orchestrator Squad** | 10, 11 | Orchestration agent, LangGraph, review workflow |
| **Delivery Agents Squad** | 12, 13, 14, 15 | Backend, Frontend, DB, Integration, DevOps, Infra agents |
| **QA & Test Squad** | 16, 17 | QA Automation agent, Integration Test agent |
| **Governance Squad** | 18, 19, 20 | Hooks, Registry, Health Monitor |
| **Intelligence Squad** | 21, 22, 23, 24 | PR Review, Story Gen, Vulnerability, Fleet Upgrade |
| **Platform Squad** | 25 | Ecosystem agents, sovereignty, compliance |

---

## How Each Phase Is Structured

Every phase folder contains:

```
phase-XX/
├── phase-XX.md          ← Main execution plan (objectives, tasks, validation, gate)
├── instructions.md      ← Copilot/Cursor instructions for AI tools in this phase
├── skills/              ← Skill packages authored or used in this phase
├── hooks/               ← OPA/Rego hooks introduced in this phase
├── prompts/             ← AI agent prompt templates for this phase
├── workflows/           ← Temporal.io / LangGraph workflow definitions
└── external-refs.md     ← External references, docs, and standards
```

---

## Quick Start for a New Team Member

1. Read this README fully.
2. Read [00-overview/project-charter.md](00-overview/project-charter.md).
3. Find your squad in the squad model above.
4. Read your phase's `phase-XX.md` to understand what you're building.
5. Read `phase-XX/instructions.md` and add it to your IDE (Copilot/Cursor) as a custom instruction.
6. Reference `shared/skills/` and `shared/instructions/` for cross-cutting standards.
7. Never skip a Gate review — Gates are hard stops.

---

## Infrastructure Cost Estimates

> All figures are approximate monthly recurring costs (AED) at steady-state operation. One-time setup costs (data migration, initial configuration) are excluded.

| Component | Service | Dev/Staging | Production | Notes |
|-----------|---------|-------------|------------|-------|
| AKS Cluster | Azure AKS | AED 2,200 | AED 6,800 | 3-node dev / 6-node prod (D8s v5) |
| GPU Node Pool | AKS + A100 | — | AED 14,400 | 2× NC24ads_A100 (sovereign LLM, Phase 25) |
| PostgreSQL | CloudNativePG | AED 400 | AED 1,200 | 3-node HA |
| EventStoreDB | AKS StatefulSet | AED 300 | AED 900 | 3-node cluster |
| Redis Cluster | AKS StatefulSet | AED 200 | AED 600 | 3-node |
| Kafka | Strimzi on AKS | AED 400 | AED 1,100 | 3-broker |
| Container Registry | Azure ACR | AED 150 | AED 450 | Standard tier |
| Key Vault / Vault | HashiCorp + Azure | AED 200 | AED 600 | |
| LLM (Premium — Claude) | Anthropic API | ~AED 1,800 | ~AED 7,300 | Varies with usage |
| LLM (Standard — GPT-4o) | Azure OpenAI | ~AED 900 | ~AED 3,700 | Varies with usage |
| LLM (Economy — DeepSeek) | DeepSeek API | ~AED 180 | ~AED 730 | Varies with usage |
| Observability | Azure Monitor + Grafana | AED 600 | AED 1,800 | |
| GitLab CI Minutes | GitLab.com | AED 400 | AED 1,100 | |
| **Total (excl. GPU)** | | **~AED 7,700** | **~AED 25,300** | |
| **Total (incl. GPU)** | | **~AED 7,700** | **~AED 39,700** | Phase 25 onwards |

> **LLM Budget Per Project Tier:**
> - Pilot: AED 183/month (≈ $50)
> - Standard: AED 735/month (≈ $200)
> - Premium: AED 3,670/month (≈ $1,000)

---

## Phase Interdependency Diagram

```
Phase 01 ──┬── Phase 02 ──┬── Phase 03 ──┬── Phase 04
           │              │              └── Phase 05 ──── Phase 06
           │              └──────────────────────────────┐
           │                                             │
           └─── (AKS infra)                              │
                                                         ▼
Phase 07 ◄── Phase 03                          Phase 07 ── Phase 08 ── Phase 09
    │                                                                      │
    └──────────────────────────────────────────────────────────────────────┤
                                                                           │
Phase 10 ◄── Phase 06 + Phase 07 + Phase 08 ◄──────────────────────────────┘
    │
    ├── Phase 11 ─┬── Phase 12 ──┬── Phase 16
    │             └── Phase 13 ──┤
    │                            ├── Phase 14
    │                            └── Phase 15 ── Phase 17
    │
    └── Phase 18 ──┬── Phase 19 ── Phase 20 ──► Gate 2
                   └────────────────────────────────────┐
                                                        │
Phase 21 ◄── Phase 12 + Phase 18                        │
Phase 22 ◄── Phase 09 + Phase 10                        │
Phase 23 ◄── Phase 19 + Phase 18 ◄──────────────────────┘
Phase 24 ◄── Phase 19 + Phase 23 + Phase 15
    │
    └──► Gate 3 ──► Phase 25 (ALL PREVIOUS) ──► Gate 4
```

---

## Troubleshooting

### "The Portal says my BRD is too ambiguous to process"
The `brd-parser` prompt requires at least 3 user roles, 5 acceptance criteria, and 2 identified bounded contexts. Review `shared/prompts/brd-parser.md` for the minimum input requirements. Consider adding an HLD to supplement the BRD.

### "LLM tier is being downgraded to economy on every task"
Check `shared/hooks/llm-tier-selection.rego`. If the project's task has `sensitivity: LOW` and the action type is `bulk_generation`, the policy intentionally routes to economy. If this is incorrect, the project's sensitivity classification may need updating in the Portal project settings.

### "Hook Engine is denying my action — no clear reason"
Run the OPA decision log query:
```bash
kubectl logs -n ai-portal-governance deploy/hook-engine | grep '"result":{"allow":false}'
```
The `deny` array in the response contains human-readable reasons. Common causes: missing approval for gated action, budget exceeded, role lacks required permission.

### "Temporal workflow is stuck in RUNNING state"
Check the Temporal Web UI (`https://temporal.adports.ae`) for the workflow. Common causes:
- Waiting for a signal (approval required — send via Portal UI)
- Activity failing — inspect activity logs for retry exhaustion
- Worker offline — check `kubectl get pods -n ai-portal-orchestration`

### "ArgoCD application shows 'OutOfSync' but no changes were made"
This usually means a Helm chart value was changed outside of GitOps. Run:
```bash
argocd app diff ai-portal-{service}-{env}
```
Never run `kubectl apply` directly — commit the change to the GitLab repository.

### "generated code fails dotnet build — 'type not found'"
The Backend Specialist Agent may have referenced a type that doesn't exist in the Scriban template context. Check `phases/phase-12/instructions.md` for the required template variable list and ensure the WorkPackage includes all required entity definitions.

### "Playwright tests fail with 'element not found'"
The generated Angular component may be missing `data-testid` attributes. The Frontend Specialist Agent adds `data-testid` automatically — if absent, re-run the Frontend Agent for that component. See `phases/phase-14/instructions.md` for the required attribute pattern.

---

*AI Portal Implementation Plan — v2.3 — 2025*  
*Classification: Internal / Confidential*
