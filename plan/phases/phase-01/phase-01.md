# Phase 01 — Platform Foundation & Infrastructure Setup

## Summary

Stand up the foundational infrastructure on which every subsequent component runs. This phase produces a fully operational AKS-based platform with all persistence, messaging, caching, and security primitives in place. Nothing else can be built until this phase is complete.

---

## Objectives

1. Provision AKS cluster with correct node pools, NSG rules, and private networking.
2. Deploy and configure PostgreSQL (HA, connection pooling via PgBouncer).
3. Deploy Redis Cluster for hot-cache and session state.
4. Deploy Apache Kafka for event streaming (stage transitions, audit events).
5. Deploy EventStoreDB as the Pipeline Ledger backbone.
6. Deploy HashiCorp Vault for secrets management.
7. Deploy Keycloak as the Portal identity provider.
8. Deploy Kong Ingress Controller and cert-manager (wildcard TLS).
9. Deploy ArgoCD for GitOps continuous delivery.
10. Deploy OpenTelemetry Collector + Prometheus + Grafana + Loki + Tempo for observability.
11. Establish a baseline Helm chart structure and ArgoCD app-of-apps pattern.

---

## Prerequisites

- Azure subscription with sufficient quota (see sizing guide below).
- Azure DevOps or GitLab repository created for `ai-portal` monorepo.
- Domain name and DNS zones configured in Azure DNS.
- Agreed AKS node pool sizing with budget sign-off.
- Vault licence or OSS decision confirmed.
- LangSmith account (for Phase 10 readiness).

---

## Duration

**3 weeks** (2-week sprint × 1.5, overlapping with Phase 02 start in week 3)

**Squad:** Infra Squad (3 engineers)

---

## Deliverables

| # | Deliverable | Acceptance Criterion |
|---|------------|---------------------|
| D1 | AKS cluster (`ai-portal-prod` + `ai-portal-dev`) | `kubectl get nodes` shows all nodes Ready |
| D2 | PostgreSQL HA (primary + replica) | Failover test passes; connection string in Vault |
| D3 | Redis Cluster (3-node) | Cluster info shows all slots assigned |
| D4 | Apache Kafka (3-broker) | Topic creation and consume/produce verified |
| D5 | EventStoreDB single node (dev) / 3-node cluster (prod) | Append + read event verified |
| D6 | HashiCorp Vault (dev mode → sealed prod) | Secret write/read + Kubernetes auth method working |
| D7 | Keycloak (Portal realm seeded) | Admin login works; `ai-portal` realm created |
| D8 | Kong Ingress + cert-manager | TLS wildcard cert valid; sample ingress resolves |
| D9 | ArgoCD with app-of-apps | First Helm app deployed via GitOps |
| D10 | Observability stack | Grafana dashboard shows AKS metrics; Loki has logs |
| D11 | Pulumi stack for all above | `pulumi up` from clean state recreates entire cluster |
| D12 | Runbook for each service | Day-2 operations documented |

---

## Technical Implementation

### AKS Cluster Architecture

```
ai-portal-dev  (single region, eastus, dev/test workloads)
├── System node pool: 3× Standard_D4s_v5 (4 vCPU, 16 GB)
├── App node pool:    3× Standard_D8s_v5 (8 vCPU, 32 GB)
└── GPU pool:         0 (reserved for Phase 4 self-hosted LLM)

ai-portal-prod (single region, eastus, production Portal)
├── System node pool: 3× Standard_D4s_v5
├── App node pool:    5× Standard_D8s_v5 (auto-scale 3–10)
└── Spot pool:        Spot Standard_D8s_v5 (for batch fleet jobs)
```

### Namespace Layout

```
ai-portal-system       ← Kong, cert-manager, ArgoCD, monitoring
ai-portal-core         ← Portal backend, Portal UI, Ledger service
ai-portal-data         ← Postgres, Redis, Kafka, EventStoreDB
ai-portal-agents       ← All specialist agents
ai-portal-vault        ← HashiCorp Vault
ai-portal-keycloak     ← Keycloak
ai-portal-observability ← Prometheus, Grafana, Loki, Tempo, OTEL Collector
```

### PostgreSQL Setup

- **Operator:** CloudNativePG (CNPG) for HA lifecycle management.
- **Databases on initial cluster:**
  - `ai_portal_core` — Portal projects, users, registry, ledger index
  - `ai_portal_keycloak` — Keycloak data
  - `ai_portal_context` — Shared project context metadata
- **Connection pooling:** PgBouncer sidecar, transaction-mode pooling.
- **Backups:** Daily PITR to Azure Blob; 30-day retention.
- **TLS:** Enforced; cert from cert-manager.

### Redis Cluster

- 3 masters, 3 replicas using Redis Cluster mode.
- Namespaced key prefixes: `portal:`, `context:`, `session:`, `cache:`.
- Eviction policy: `allkeys-lru` for the cache namespace.
- Persistence: RDB snapshots every 15 minutes + AOF for session/context.

### Kafka Setup

- **Operator:** Strimzi Kafka Operator.
- **Topics to create on Day 1:**
  - `portal.ledger.events` — all Pipeline Ledger events (retention: 30 days)
  - `portal.stage.transitions` — real-time stage progress (retention: 7 days)
  - `portal.health.probes` — health check results (retention: 3 days)
  - `portal.notifications` — outbound notification queue (retention: 1 day)

### Vault Setup

- **Auth methods:** Kubernetes (primary), LDAP/Keycloak OIDC (for human operators).
- **Secret engines:** KV-v2 for static secrets; database dynamic credentials for Postgres.
- **Policies:** One policy per namespace; least-privilege.
- **PKI engine:** For internal TLS certificates.
- **Initial secrets seeded:** LLM API keys, GitLab tokens, Azure DevOps PATs, SonarQube tokens, Checkmarx API key.

### Keycloak Setup (Portal Realm)

- **Realm:** `ai-portal`
- **Client:** `portal-web` (OIDC, public)
- **Groups:** `architects`, `tech-leads`, `platform-engineers`, `developers`, `ba-pm`, `qa-engineers`, `security-engineers`, `sre`, `compliance`, `leadership`
- **Realm roles:** `portal:read`, `portal:write`, `portal:approve`, `portal:admin`, `ledger:query`, `fleet:manage`, `health:configure`
- Import base realm JSON from `shared/specs/adports-keycloak-realm.schema.json`

### Observability Stack

```yaml
# Components deployed via Helm
kube-prometheus-stack:    # Prometheus + Grafana + Alertmanager
  version: 62.x
loki-stack:               # Loki + Promtail
  version: 2.10.x
tempo:                    # Distributed tracing
  version: 1.10.x
opentelemetry-collector:  # OTEL collector
  version: 0.107.x
```

Initial dashboards to import:
- AKS cluster overview
- Postgres query performance
- Redis memory and hit rate
- Kafka consumer lag
- EventStoreDB event throughput

---

## Step-by-Step Execution Plan

### Week 1

**Day 1–2:**
- [ ] Create Azure resource groups, VNets, subnets, NSGs via Pulumi.
- [ ] Provision AKS dev cluster.
- [ ] Install cert-manager + wildcard TLS cert.
- [ ] Install Kong Ingress Controller.

**Day 3–4:**
- [ ] Deploy CloudNativePG operator + Postgres cluster.
- [ ] Create databases, seed Keycloak DB.
- [ ] Configure PgBouncer.
- [ ] Write Postgres connection string to Vault.

**Day 5:**
- [ ] Deploy Redis Cluster via Helm.
- [ ] Smoke test cluster connectivity.
- [ ] Write Redis password to Vault.

### Week 2

**Day 6–7:**
- [ ] Deploy Strimzi Kafka operator + Kafka cluster.
- [ ] Create initial Kafka topics.
- [ ] Smoke test produce/consume.

**Day 8–9:**
- [ ] Deploy EventStoreDB.
- [ ] Smoke test event append + read.
- [ ] Configure EventStoreDB admin credentials in Vault.

**Day 10:**
- [ ] Deploy HashiCorp Vault.
- [ ] Configure Kubernetes auth method.
- [ ] Write initial secrets (LLM keys, CI tokens, etc.).
- [ ] Configure PKI engine and issue first internal cert.

### Week 3

**Day 11–12:**
- [ ] Deploy Keycloak.
- [ ] Import `ai-portal` realm.
- [ ] Create groups, roles, initial admin users.
- [ ] Test OIDC flow with sample client.

**Day 13–14:**
- [ ] Deploy ArgoCD + app-of-apps.
- [ ] Register all above services as ArgoCD applications.
- [ ] First GitOps deploy (push a change, verify ArgoCD applies it).

**Day 15:**
- [ ] Deploy observability stack.
- [ ] Import initial dashboards.
- [ ] Configure Alertmanager → Teams channel.
- [ ] Provision prod cluster (parallel to last dev tasks).

---

## Validation & Testing

### Infrastructure Tests (automated, in CI)

```bash
# Run from Pulumi test suite
pulumi preview --expect-no-changes  # infrastructure is converged
kubectl get pods -A --field-selector=status.phase!=Running  # all pods running
```

### Connectivity Smoke Tests

```bash
# PostgreSQL
psql postgresql://health_check:${PG_PW}@pgbouncer.ai-portal-data:5432/ai_portal_core -c "SELECT 1;"

# Redis
redis-cli -h redis-cluster.ai-portal-data -a ${REDIS_PW} cluster info | grep cluster_state:ok

# Kafka
kafka-topics.sh --list --bootstrap-server kafka.ai-portal-data:9092

# EventStoreDB
curl -u admin:${ESDB_PW} http://eventstore.ai-portal-data:2113/info

# Keycloak
curl -s https://auth.adports-ai.internal/health/ready | grep -q '"status":"UP"'

# Vault
vault status -address=https://vault.ai-portal-vault.svc.cluster.local
```

### Security Checks

- [ ] All services using TLS (no plaintext connections).
- [ ] Vault transit encryption on sensitive Postgres columns.
- [ ] Network policies in place (pods can only communicate with declared neighbours).
- [ ] No secrets in Kubernetes Secrets — all from Vault via vault-agent-injector.
- [ ] CIS AKS Benchmark scan passes with no critical findings.

---

## Gate Criterion

**Phase 01 is complete when:**
- All 12 deliverables pass acceptance criteria.
- All smoke tests pass from a clean namespace.
- Pulumi `preview` shows no drift.
- Security checklist is 100% complete.
- Runbooks are reviewed by a second engineer.
- Phase 02 can begin (team confirmed ready).

---

## Risks Specific to This Phase

| Risk | Mitigation |
|------|-----------|
| Azure quota limits hit | Pre-request quota increase before phase starts |
| CloudNativePG learning curve | Use official CNPG examples; allocate Day 3 for learning |
| Vault seal/unseal complexity | Start with dev mode; harden in week 2 |
| Keycloak realm import issues | Validate realm JSON schema against spec before import |
| Networking complexity (private AKS) | Use reference architecture from Azure official docs |

---

## References

- See [external-refs.md](external-refs.md) for links to official docs.
- See [shared/skills/infrastructure-setup.md](../../shared/skills/infrastructure-setup.md) for the AD Ports infra skill.
- See [shared/hooks/infra-provisioning.rego](../../shared/hooks/infra-provisioning.rego) for provisioning guardrails.
- See [workflows/infra-provision-workflow.md](workflows/infra-provision-workflow.md) for the full provisioning workflow.

---

*Phase 01 — Platform Foundation — AI Portal — v1.0*
