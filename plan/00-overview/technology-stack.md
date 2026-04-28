# Technology Stack — Build vs. Integrate Decisions

> **Principle:** Build only what creates unique value for AD Ports. Integrate proven open-source for everything else.

---

## Full Stack Reference

| Category | Technology | Version | Role | Decision | Owner |
|----------|-----------|---------|------|----------|-------|
| **Portal UI** | Angular + PrimeNG + Tailwind CSS | Angular 20, PrimeNG 18 | Web UI consistent with JUL/PCS | **Build** (thin shell) | Core Squad |
| **Portal Backend** | .NET 9 + MediatR + FluentValidation + EF Core | .NET 9 LTS | Portal's own API, CQRS pattern | **Build** (thin) | Core Squad |
| **Orchestration Workflow** | LangGraph | 0.2.x | Deterministic agent state machines | **Integrate** | Orchestrator Squad |
| **Multi-agent Patterns** | CrewAI | 0.80.x | Team-based agent collaboration | **Integrate** | Orchestrator Squad |
| **LLM Gateway** | LiteLLM | 1.x | Provider-agnostic routing, caching, cost tracking | **Integrate** | Orchestrator Squad |
| **LLMs — Judgment** | Claude Sonnet 4.x + GPT-4o | Latest | Premium reasoning: intent extraction, review | **Integrate** | Orchestrator Squad |
| **LLMs — Routine** | DeepSeek-V3 / Llama 3.3-70B | Latest | Cheap routine generation, code completion | **Integrate** | Orchestrator Squad |
| **Agent Protocols** | MCP (Model Context Protocol) + A2A | MCP 1.x | Tool & agent interoperability | **Integrate** | Fabric Squad |
| **Agent Observability** | LangSmith + OpenTelemetry | Latest | Multi-agent traces, cost visibility | **Integrate** | Infra Squad |
| **Durable Workflow** | Temporal.io | 1.x | Long-running orchestrations, fleet campaigns | **Integrate** | Orchestrator Squad |
| **Event Bus** | Apache Kafka | 3.7.x | Stage transitions, audit events, async messaging | **Integrate** | Infra Squad |
| **Immutable Event Store** | EventStoreDB | 24.x | Pipeline Ledger backbone | **Integrate** | Core Squad |
| **Relational DB** | PostgreSQL | 16.x | Projects, users, registry, ledger index, Portal data | **Integrate** | Infra Squad |
| **Hot Cache** | Redis Cluster | 7.2.x | Shared project context, session state | **Integrate** | Infra Squad |
| **Object Store** | MinIO | RELEASE.2024-x | On-prem S3-compatible artifact store; abstracted behind S3 interface for future AKS/Azure Blob swap | **Integrate** | Infra Squad |
| **Identity** | Keycloak | 25.x | Portal identity + managed project realms | **Integrate** | Infra Squad |
| **Authorization** | OpenFGA | 1.x | Fine-grained Portal permissions | **Integrate** | Core Squad |
| **Secrets** | HashiCorp Vault | 1.17.x | Credentials for all target systems | **Integrate** | Infra Squad |
| **Policy Engine** | OPA (Open Policy Agent) + Rego | 0.68.x | Hook Engine evaluation | **Integrate** | Governance Squad |
| **Digital Signatures** | Keycloak + X.509 | — | Approval signing for Pipeline Ledger | **Integrate** | Governance Squad |
| **Health Monitoring** | Prometheus + Alertmanager + Blackbox Exporter | Latest | Probe execution and routing | **Integrate** | Governance Squad |
| **Synthetic Monitoring** | Newman (Postman CLI) | 6.x | Integration-test synthetics | **Integrate** | QA Squad |
| **SAST** | Checkmarx One + Semgrep | Latest | PR & pipeline static analysis | **Integrate** | QA Squad |
| **SCA** | Snyk + Trivy | Latest | Dependency & container scanning | **Integrate** | QA Squad |
| **Code Quality** | SonarQube | 10.x | Quality gate enforcement | **Integrate** | QA Squad |
| **Container Platform** | VMware Tanzu Kubernetes Grid (TKG) | 2.x (on vSphere 8) | **Primary**: on-premise Portal runtime + all generated projects. **Future**: AKS (Azure) supported via provider-abstracted Pulumi stacks | **Integrate** | Infra Squad |
| **Container Registry** | Harbor | 2.x | On-prem OCI registry (Tanzu-native); ACR used when targeting AKS | **Integrate** | Infra Squad |
| **GitOps** | ArgoCD | 2.12.x | Continuous delivery | **Integrate** | Infra Squad |
| **IaC** | Pulumi + Crossplane | Pulumi 3.x | Infrastructure management | **Integrate** | Delivery Agents Squad |
| **E2E Testing** | Playwright | 1.47.x | QA automation | **Integrate** | QA Squad |
| **API Testing** | Postman / Newman | Newman 6.x | Deployed-system verification | **Integrate** | QA Squad |
| **Contract Testing** | Pact | 12.x | Consumer-driven contracts | **Integrate** | QA Squad |
| **Load Testing** | k6 | 0.54.x | Performance validation | **Integrate** | QA Squad |
| **Observability** | OpenTelemetry + Prometheus + Grafana + Loki + Tempo | Latest | Full-stack telemetry | **Integrate** | Infra Squad |
| **Documentation** | Docusaurus | 3.x | Generated spec sites for all projects | **Integrate** | Delivery Agents Squad |
| **Diagrams** | draw.io (diagrams.net) | 24.x | Architecture visuals | **Integrate** | Orchestrator Squad |
| **Work Items** | Jira + Azure DevOps (native APIs via MCP) | — | Story and ticket management | **Integrate** | Fabric Squad |
| **Notifications** | Teams + Slack + PagerDuty (native APIs) | — | Alert channels | **Integrate** | Governance Squad |

---

## What We BUILD (Unique Value Layer)

These are the AD Ports-specific components that create defensible value:

| Component | Description | Phase |
|-----------|-------------|-------|
| **MCP Skill Packages** | Packaged how-tos encoding AD Ports architectural knowledge | 07 |
| **MCP Spec Library** | Machine-readable contracts: Keycloak realm, Helm values, MPay OpenAPI | 07 |
| **MCP Instruction Library** | Policy-as-text: coding standards, security baseline, lifecycle policy | 07 |
| **Keycloak MCP Server** | Tools: list-realms, create-client, add-role, configure-group | 08 |
| **Standards MCP Server** | Tools: fetch-coding-standard, list-approved-libraries, get-naming-conventions | 08 |
| **GitLab/Azure DevOps MCP** | Tools: create-project, protect-branch, run-pipeline, read-logs | 09 |
| **Kubernetes MCP Server** | Tools: list-namespaces, apply-helm, read-pod-logs (Tanzu-first; works on any K8s including AKS) | 09 |
| **Orchestrator State Machine** | LangGraph workflow: intent→standards→proposal→review→delegate→consolidate | 10 |
| **Orchestrator Logic** | Intent extraction, standards retrieval, component decomposition | 10 |
| **PR Review Rubric** | Scoring model calibrated to AD Ports C# and Angular standards | 21 |
| **Ticket Implementation Agent** | Bounded-scope implementer with opt-in activation model | 22 |
| **Framework Migration Playbooks** | .NET, Angular, Node.js, Postgres per-framework migration guides | 24 |
| **Fleet Upgrade Agent** | Campaign orchestration with wave planning and verification | 24 |
| **Project Registry** | Fleet inventory with stack fingerprinting and stack-query API | 19 |
| **Pipeline Ledger** | Immutable audit with cryptographic chaining | 05 |
| **Service Health Monitor** | Probe orchestration + admin UI + notifications + ledger integration | 20 |
| **Integration Test Agent** | Postman-collection generator with BRD-aware realistic payloads | 17 |
| **MPay Ecosystem Agent** | Full spec + skills + MCP + sample code + sandbox paths | 25 |
| **Keycloak Ecosystem Agent** | Universal dependency — full AD Ports realm conventions | 25 |
| **CRM/CMS/ERP/JUL/PCS Agents** | Per-system ecosystem adapters | 25 |
| **Hook Engine** | OPA/Rego pre/post hooks, budget enforcement, two-person approval | 18 |
| **Shared Project Context** | Redis-backed team-shared AI collaboration memory | 06 |

---

## Version Pinning Strategy

- All **Integrate** components: pin to a specific minor version; upgrade via Fleet Campaign.
- All **Build** components: semantic versioning; breaking changes trigger required updates in consumers.
- Framework versions tracked in the **Project Registry** stack fingerprint.
- Upgrade eligibility assessed by the **Framework Obsolescence Monitor** (Phase 23).

---

## LLM Provider Strategy

| Tier | Provider | Use Cases | Cost Profile |
|------|----------|-----------|-------------|
| Premium | Anthropic Claude Sonnet 4.x | Intent extraction, architecture reasoning, PR review narrative | High, bounded |
| Standard | Azure OpenAI GPT-4o | Code generation, spec synthesis, story generation | Medium |
| Economy | DeepSeek-V3 / Llama 3.3 (self-hosted) | Routine generation, boilerplate, documentation | Low / near-zero |
| Sovereign | Self-hosted Llama (TKG GPU nodes, on-premise vSphere) | Classified projects, ARCCLA workloads | Phase 25 |

LiteLLM gateway routes by declared task tier, with fallback chains per provider outage.

---

## Multi-Cloud / Multi-Platform Strategy

The platform is designed to run on-premise (Tanzu) first but remain portable to AKS.

| Concern | On-Prem (Tanzu) — Primary | AKS — Future |
|---------|--------------------------|-------------|
| K8s distro | TKG 2.x on vSphere 8 | AKS 1.30.x |
| IaC provider | `@pulumi/vsphere` + `@pulumi/kubernetes` | `@pulumi/azure-native` + `@pulumi/kubernetes` |
| Container registry | Harbor 2.x | ACR (Azure Container Registry) |
| Object storage | MinIO (S3-compatible API) | Azure Blob (via S3-compatible endpoint or native SDK) |
| Load balancer | MetalLB (or NSX-T if available) | Azure Load Balancer (managed by AKS) |
| CNI | Antrea (TKG default) | Azure CNI Overlay |
| DNS | Internal AD/NSX-T DNS | Azure DNS |
| Secrets backend | HashiCorp Vault (K8s auth) | HashiCorp Vault (K8s auth) — same |

**Portability rule:** All application-layer Helm charts and ArgoCD applications are cloud-agnostic. Only the `src/infrastructure/stacks/` Pulumi stacks differ per target. Storage access is always via the `IObjectStore` S3-compatible interface.

---

## Local Development Prerequisites

```bash
# Required tools for every developer
node >= 22.x
dotnet-sdk >= 9.0
docker >= 27.x
kubectl >= 1.30.x
helm >= 3.16.x
pulumi >= 3.x
python >= 3.12  # for LangGraph/LiteLLM
poetry >= 1.8   # Python package management
adports-ai CLI  # installed after Phase 08
```

---

*Technology Stack — AI Portal — v1.0 — April 2026*
