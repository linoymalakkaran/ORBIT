# ORBIT — Orchestrated Repository & Build Intelligence Toolkit

> **AD Ports AI Portal** — One portal. All agents. Every standard. Forever maintained.

ORBIT is the enterprise AI orchestration platform for AD Ports Group. It turns business documents (BRDs, HLDs, ICDs) into production-ready, standards-compliant microservices — from identity provisioning to Kubernetes deployment — orchestrated by AI agents with full audit trail.

---

## Repository Structure

```
ORBIT/
├── .github/                    ← PR template, issue templates, CI workflows (Phase 15)
├── docs/
│   ├── whitepaper/             ← AI Portal Platform Whitepaper
│   └── diagrams/               ← Architecture diagrams (.drawio)
├── plan/                       ← Complete 25-phase implementation plan
│   ├── 00-overview/            ← Charter, tech stack, team, metrics, risks, glossary
│   ├── phases/phase-01…25/     ← Phase specs + IDE instructions + external refs
│   └── shared/                 ← Skills, specs, hooks, prompts, workflows, instructions
├── src/                        ← Source code (populated phase by phase)
│   ├── portal-ui/              ← Angular 20 + PrimeNG 18 + NX (Phase 04)
│   ├── portal-api/             ← .NET 9 CQRS backend (Phase 03)
│   ├── orchestrator/           ← Python LangGraph + Temporal (Phase 10)
│   ├── mcp-servers/            ← Python FastAPI MCP servers (Phase 08–09)
│   ├── hook-engine/            ← OPA/Rego + FastAPI (Phase 18)
│   └── infrastructure/         ← Pulumi IaC + Helm charts (Phase 01, 15)
├── .gitattributes
├── .gitignore
├── CHANGELOG.md
├── CONTRIBUTING.md
└── README.md                   ← You are here
```

---

## The Four Gates

| Gate | End of Phase | Milestone |
|------|-------------|-----------|
| **Gate 1** | Phase 15 | Portal generates, builds & deploys a real AD Ports service end-to-end |
| **Gate 2** | Phase 20 | Pilot projects onboarded; PR Review Agent ≥85% agreement |
| **Gate 3** | Phase 24 | Fleet campaigns live; Ticket Agent at acceptable merge rate |
| **Gate 4** | Phase 25 | Sovereign LLM deployed; NESA compliance delivered |

---

## Quick Start for New Team Members

1. Read [plan/README.md](plan/README.md) — full phase index & navigation
2. Read [plan/00-overview/project-charter.md](plan/00-overview/project-charter.md)
3. Find your squad in [plan/00-overview/team-structure.md](plan/00-overview/team-structure.md)
4. Open your phase folder: `plan/phases/phase-{NN}/`
5. Add `plan/phases/phase-{NN}/instructions.md` to your IDE (Copilot / Cursor) as a custom instruction
6. Reference `plan/shared/` for cross-cutting skills, specs, and standards

---

## Technology Stack

| Layer | Technology |
|-------|-----------|
| Portal UI | Angular 20 + PrimeNG 18 + Tailwind CSS + NX |
| Portal API | .NET 9, CQRS (MediatR + FluentValidation + EF Core) |
| Orchestration | LangGraph (Python) + Temporal.io |
| LLM Gateway | LiteLLM (Claude Sonnet 4 / GPT-4o / DeepSeek-V3 / Llama 3.3) |
| Identity | Keycloak 25 + OpenFGA |
| Audit Ledger | EventStoreDB + Kafka + PostgreSQL |
| Policy Engine | OPA / Rego (Hook Engine) |
| Secrets | HashiCorp Vault |
| Container | AKS 1.30 + CloudNativePG + Strimzi + Redis Cluster |
| GitOps | ArgoCD + Pulumi TypeScript |
| Observability | OpenTelemetry + Prometheus + Grafana + Loki + Tempo |

---

## Links

- [Implementation Plan](plan/README.md)
- [Glossary](plan/00-overview/glossary.md)
- [Risk Register](plan/00-overview/risk-register.md)
- [CHANGELOG](CHANGELOG.md)
- [CONTRIBUTING](CONTRIBUTING.md)
- [Whitepaper](docs/whitepaper/AI-Portal-Platform-Whitepaper-Draft-v3.md)
- [Architecture Overview](docs/ARCHITECTURE.md)
- [Operational Runbook](docs/RUNBOOK.md)

---

*Classification: Internal / Confidential — AD Ports Group*
