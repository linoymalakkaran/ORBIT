# Team Structure & Squad Model

## Overview

The AI Portal is built by **9 specialized squads**, each owning a coherent vertical slice of the platform. Squads operate on 2-week sprints. Each squad has full autonomy within its slice but coordinates through defined interfaces (APIs, MCP contracts, shared skills).

---

## Squad Definitions

### 1. Infra Squad
**Phases:** 01, 02  
**Focus:** Platform foundation — every service the platform runs on.

| Role | Count | Responsibilities |
|------|-------|----------------|
| Senior DevOps Engineer | 1 | TKG cluster (on-prem Tanzu), cert-manager, Kong ingress, ArgoCD, MetalLB |
| Platform Engineer | 1 | Postgres HA, Redis Cluster, Kafka, EventStoreDB |
| Security Engineer | 1 | Keycloak setup, Vault, NSX-T / Network Policies, Harbor registry |

**Outputs:** Running infrastructure, Helm charts, Terraform/Pulumi modules, Keycloak base realm.

---

### 2. Core Squad
**Phases:** 03, 04, 05, 06  
**Focus:** Portal API, Portal UI, Pipeline Ledger, Shared Context.

| Role | Count | Responsibilities |
|------|-------|----------------|
| Senior .NET Engineer | 2 | Portal backend CQRS, EF Core, OpenFGA integration |
| Senior Angular Engineer | 2 | Portal UI, navigation, approval surfaces |
| Full-Stack Engineer | 1 | Pipeline Ledger API + UI component |

**Outputs:** Portal backend, Portal frontend, Ledger service, Redis context layer.

---

### 3. Fabric Squad
**Phases:** 07, 08, 09  
**Focus:** Skills, Specs, Instructions library; MCP server implementations.

| Role | Count | Responsibilities |
|------|-------|----------------|
| Principal Architect | 1 | Skills/specs/instructions authoring, quality reviews |
| Senior .NET Engineer | 1 | MCP server implementations (Keycloak, GitLab, Kubernetes/Tanzu) |
| Python Engineer | 1 | MCP server implementations (Jira, Postgres, SonarQube) |
| Technical Writer | 1 | Instruction documents, skill documentation |

**Outputs:** Skill library (≥15 skills), MCP servers (≥10), spec schemas, instruction library.

---

### 4. Orchestrator Squad
**Phases:** 10, 11  
**Focus:** Orchestration Agent (LangGraph), architecture proposal, review workflow.

| Role | Count | Responsibilities |
|------|-------|----------------|
| ML/AI Engineer | 2 | LangGraph state machine, LiteLLM gateway, intent extraction |
| Senior .NET Engineer | 1 | Review workflow API, approval tracking |
| Python Engineer | 1 | Agent-to-agent protocols, Temporal.io workflows |

**Outputs:** Orchestration Agent, intent extraction, proposal generation, review workflow.

---

### 5. Delivery Agents Squad
**Phases:** 12, 13, 14, 15  
**Focus:** All specialist delivery agents — scaffolding, pipelines, infrastructure.

| Role | Count | Responsibilities |
|------|-------|----------------|
| Senior .NET Engineer | 2 | Backend Agent templates, CQRS scaffold, Dockerfile generation |
| Senior Angular Engineer | 1 | Frontend Agent, Nx workspace, Native Federation templates |
| DevOps Engineer | 2 | DevOps Agent, pipeline templates, GitLab CI, Azure DevOps |
| Platform Engineer | 1 | Infrastructure Agent, Pulumi templates, Helm chart generation |
| Python/AI Engineer | 1 | Agent framework, DB Agent, Integration Agent |

**Outputs:** Backend, Frontend, Database, Integration, DevOps, Infrastructure, Observability agents.

---

### 6. QA & Test Squad
**Phases:** 16, 17  
**Focus:** QA Automation Agent, Integration Test Agent.

| Role | Count | Responsibilities |
|------|-------|----------------|
| Senior QA Engineer | 2 | Playwright framework, k6 load tests, Axe accessibility |
| Python/AI Engineer | 1 | QA Agent, test-generation logic |
| API Test Engineer | 1 | Postman/Newman agent, multi-environment matrix |

**Outputs:** QA Automation Agent, Integration Test Agent, Common QA Framework NuGet/npm packages.

---

### 7. Governance Squad
**Phases:** 18, 19, 20  
**Focus:** Hook Engine, Project Registry, Service Health Monitor.

| Role | Count | Responsibilities |
|------|-------|----------------|
| Platform Engineer | 1 | OPA/Rego hooks, policy engine |
| Senior .NET Engineer | 1 | Project Registry API, stack fingerprinting |
| SRE / DevOps Engineer | 2 | Health Monitor, probe execution, notification channels |
| Frontend Engineer | 1 | Health Monitor admin UI |

**Outputs:** Hook Engine, Project Registry, Service Health Monitor.

---

### 8. Intelligence Squad
**Phases:** 21, 22, 23, 24  
**Focus:** PR Review, BA automation, Vulnerability Radar, Fleet Upgrade.

| Role | Count | Responsibilities |
|------|-------|----------------|
| ML/AI Engineer | 2 | PR review scoring, story generation, fleet campaign orchestration |
| Senior .NET Engineer | 1 | Ticket Implementation Agent, Jira webhook integration |
| Security Engineer | 1 | Vulnerability Radar, CVE feed integration, Checkmarx/Snyk |
| Platform Engineer | 1 | Fleet Upgrade Agent, migration playbooks, wave planning |

**Outputs:** PR Review Agent, BA/PM Story Agent, Ticket Impl Agent, Vulnerability Radar, Fleet Upgrade Agent.

---

### 9. Platform Squad
**Phase:** 25  
**Focus:** Ecosystem agents, sovereign deployment, compliance.

| Role | Count | Responsibilities |
|------|-------|----------------|
| Principal Architect | 1 | Architecture oversight, ecosystem agent design |
| Senior .NET Engineer | 2 | MPay, CRM, ERP agents |
| Integration Engineer | 2 | JUL event bus, PCS, SINTECE/ASYCUDA adapters |
| Security/DevOps Engineer | 1 | Sovereign deployment, self-hosted LLM, NESA compliance |
| Compliance Specialist | 1 | SOC-2, NESA, UAE-IAR evidence packages |

**Outputs:** All ecosystem agents, sovereign deployment playbook, compliance packages.

---

## Cross-Squad Interfaces

| Interface | Producer | Consumer | Mechanism |
|-----------|---------|---------|-----------|
| MCP server URLs | Fabric Squad | Orchestrator Squad, IDE users | MCP Registry in Portal |
| Skill/Spec/Instruction library | Fabric Squad | All squads | Portal Capability Fabric API |
| Pipeline Ledger events | Core Squad | All squads | EventStoreDB + Kafka |
| Shared Project Context API | Core Squad | Orchestrator Squad, Delivery Agents | Redis + REST API |
| Hook Engine policies | Governance Squad | All squads | OPA sidecar + HTTP decision API |
| Project Registry API | Governance Squad | Intelligence Squad, Orchestrator | REST API + MCP |
| Agent output artifacts | Delivery Agents Squad | QA Squad, Governance Squad | Artifact Store API |
| Health probe results | Governance Squad | Intelligence Squad, Core Squad | Prometheus metrics + Kafka events |

---

## Escalation Path

```
Developer → Squad Lead → Delivery Lead → Product Owner → Technical Lead → CTO
```

Gate decisions require: Technical Lead + Head of Engineering + (for high-risk gates) CTO.

---

## Onboarding Checklist for New Squad Members

- [ ] Read project charter and this team structure doc
- [ ] Get Keycloak Portal account with correct role group
- [ ] Clone the `ai-portal` monorepo
- [ ] Install local dev prerequisites (see technology-stack.md)
- [ ] Read your phase's `phase-XX.md`
- [ ] Add `phase-XX/instructions.md` to your IDE custom instructions
- [ ] Add relevant `shared/skills/` files to your IDE
- [ ] Attend your squad's next sprint planning
- [ ] Complete first contribution: a small addition to the skill library

---

*Team Structure — AI Portal — v1.0 — April 2026*
