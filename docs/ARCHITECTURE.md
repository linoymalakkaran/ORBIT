# ORBIT AI Platform — Architecture Overview

## Platform Summary

ORBIT (Operational AI Platform) is a multi-agent, cloud-native AI platform built on **VMware Tanzu Kubernetes Grid (TKG) 2.x** on **vSphere 8**. It provides a governed, auditable, end-to-end AI-powered software development lifecycle platform for Abu Dhabi Ports.

---

## Domain & Endpoints

| Service | URL |
|---|---|
| Portal UI | `https://portal.ai.adports.ae` |
| Portal API | `https://api.ai.adports.ae` |
| Keycloak (IAM) | `https://auth.ai.adports.ae` |
| Harbor (Registry) | `https://harbor.ai.adports.ae` |
| LiteLLM Gateway | `https://litellm.ai.adports.ae` |
| Grafana | `https://grafana.ai.adports.ae` |
| Temporal Web | `https://temporal.ai.adports.ae` |
| EventStoreDB | `https://esdb.ai.adports.ae` |
| ArgoCD | `https://argocd.ai.adports.ae` |

---

## Platform Architecture (25 Phases)

### Infrastructure Layer

| Phase | Component | Path | Description |
|---|---|---|---|
| 01 | Platform Foundation | `stacks/` | Pulumi TKG cluster + K8s base resources |
| 02 | Data Layer & Identity | `stacks/k8s/` | PostgreSQL, Redis, MinIO, Keycloak, HashiCorp Vault |
| 19 | LiteLLM Gateway | `infra/litellm/` | Model routing proxy (Azure OpenAI) |
| 20 | Temporal.io | `infra/temporal/` | Durable workflow engine |
| 21 | EventStoreDB + Kafka | `infra/eventstore/`, `infra/kafka/` | Event sourcing + streaming |
| 22 | Observability | `infra/observability/` | Prometheus, Grafana, Loki, Tempo, OTEL |
| 23 | GitOps | `gitops/` | ArgoCD app-of-apps ApplicationSets |

### Application Services

| Phase | Service | Path | Language | Port |
|---|---|---|---|---|
| 03 | Portal Backend API | `src/portal-api/` | .NET 9 | 8080 |
| 04 | Portal Frontend UI | `src/portal-ui/` | Angular 20 / NX | 4200 |
| 05 | Pipeline Ledger | `src/pipeline-ledger/` | Python / FastAPI | 8000 |
| 06 | Context Service | `src/portal-api/` | .NET 9 + Redis | — |
| 07 | Capability Fabric | `src/capability-fabric/` | Python / FastAPI | 8000 |
| 08 | MCP Servers (core) | `src/mcp-servers/` | Python / FastAPI | 8000 |
| 09 | MCP Servers (extended) | `src/mcp-servers/` | Python / FastAPI | 8000 |
| 10 | Orchestrator Agent | `src/orchestrator/` | Python / LangGraph | 8000 |
| 11 | Hook Engine | `src/hook-engine/` | Python / FastAPI | 8000 |
| 12 | Project Registry Agent | `src/project-registry-agent/` | Python / FastAPI | 8000 |
| 13 | Health Monitor Agent | `src/health-monitor-agent/` | Python / FastAPI | 8000 |
| 14 | PR Review Agent | `src/pr-review-agent/` | Python / LangGraph | 8000 |
| 15 | BA Agent | `src/ba-agent/` | Python / FastAPI | 8000 |
| 16 | PM Agent | `src/pm-agent/` | Python / FastAPI | 8000 |
| 17 | Vulnerability Radar | `src/vulnerability-radar-agent/` | Python / FastAPI | 8000 |
| 18 | Fleet Upgrade Agent | `src/fleet-upgrade-agent/` | Python / FastAPI | 8000 |
| — | Docs Agent | `src/docs-agent/` | Python / FastAPI | 8000 |

### Quality & Testing

| Phase | Component | Path |
|---|---|---|
| 24 | Integration Tests | `tests/integration/` |
| 25 | Documentation | `docs/` |

---

## Security Architecture

- **Identity**: Keycloak 25 (`ai-portal` realm) + OpenFGA for fine-grained RBAC
- **Secrets**: HashiCorp Vault — Vault Agent Injector pattern, zero K8s Secrets for sensitive data
- **TLS**: cert-manager + `adports-internal-ca` ClusterIssuer everywhere
- **Registry**: Harbor 2.x at `harbor.ai.adports.ae` — all images air-gapped from Docker Hub
- **Network**: MetalLB L2 + Antrea CNI; Kong 3.8 + KIC 3.3 Ingress

---

## MCP Servers

| Server | Capabilities |
|---|---|
| `keycloak-mcp` | User management, role inspection, token introspection |
| `gitlab-mcp` | MR management, diff, comments, pipeline trigger |
| `kubernetes-mcp` | Pod listing, deployment status, logs |
| `postgres-mcp` | Read-only query execution, schema inspection |
| `jira-mcp` | Issue search, creation, sprint management |
| `vault-mcp` | Secret path listing, metadata (values stripped) |
| `harbor-mcp` | Repository listing, Trivy vulnerability reports |
| `confluence-mcp` | Page retrieval, search, creation |

---

## Orchestration Pipeline Stages

LangGraph 12-stage state machine in `src/orchestrator/app/graph.py`:

1. `requirements_analysis`
2. `architecture_design`
3. `api_design`
4. `db_schema_design`
5. `iac_generation`
6. `ci_pipeline_generation`
7. `code_generation`
8. `test_generation`
9. `code_review`
10. `security_scan`
11. `documentation`
12. `pr_review`

Each stage is also a **Temporal Activity** wrapped in `OrbitPipelineWorkflow`.

---

## Data Flow

```
GitLab Webhook
    │
    ▼
Hook Engine ──► Kafka (orbit.gitlab.events)
    │
    ▼
Orchestrator (LangGraph + Temporal)
    │
    ├──► MCP Servers (GitLab, K8s, Jira, Harbor...)
    │
    ├──► LiteLLM Gateway ──► Azure OpenAI
    │
    ▼
Pipeline Ledger (EventStoreDB ──► Kafka ──► PostgreSQL read model)
    │
    ▼
Portal API (CQRS/MediatR) ──► Portal UI (Angular 20)
```

---

## Deployment

```bash
# 1. Bootstrap cluster (Pulumi)
cd stacks/tanzu && pulumi up

# 2. Install ArgoCD
kubectl apply -f https://raw.githubusercontent.com/argoproj/argo-cd/v2.12.0/manifests/install.yaml -n argocd

# 3. Deploy root app-of-apps
kubectl apply -f gitops/root-app.yaml

# ArgoCD syncs everything else automatically
```

---

## Running Integration Tests

```bash
cd tests/integration
export PORTAL_API_URL=https://api.ai.adports.ae
export KC_USERNAME=integration-test-user
export KC_PASSWORD=<secret>
pip install pytest pytest-asyncio httpx
pytest -v
```
