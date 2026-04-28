# Phase 01 — External References

## Azure & AKS

| Resource | URL | Notes |
|----------|-----|-------|
| AKS Best Practices | https://learn.microsoft.com/en-us/azure/aks/best-practices | Start here for cluster design |
| AKS Private Cluster | https://learn.microsoft.com/en-us/azure/aks/private-cluster | Use for production |
| CIS AKS Benchmark | https://www.cisecurity.org/benchmark/kubernetes | Security baseline |
| AKS Workload Identity | https://learn.microsoft.com/en-us/azure/aks/workload-identity-overview | Preferred over pod identity |
| Azure CNI Overlay | https://learn.microsoft.com/en-us/azure/aks/azure-cni-overlay | Networking option |
| Pulumi Azure Native | https://www.pulumi.com/registry/packages/azure-native/ | Pulumi provider docs |

## Databases & Storage

| Resource | URL | Notes |
|----------|-----|-------|
| CloudNativePG | https://cloudnative-pg.io/documentation/ | Postgres operator |
| CloudNativePG High Availability | https://cloudnative-pg.io/documentation/current/replication/ | HA setup guide |
| PgBouncer Config | https://www.pgbouncer.org/config.html | Connection pooler |
| Redis Cluster Tutorial | https://redis.io/docs/management/scaling/ | Cluster mode setup |
| Strimzi Kafka | https://strimzi.io/documentation/ | Kafka on Kubernetes |

## Security & Secrets

| Resource | URL | Notes |
|----------|-----|-------|
| HashiCorp Vault | https://developer.hashicorp.com/vault/docs | Core docs |
| Vault Agent Injector | https://developer.hashicorp.com/vault/docs/platform/k8s/injector | K8s secrets injection |
| Vault Kubernetes Auth | https://developer.hashicorp.com/vault/docs/auth/kubernetes | Kubernetes auth |
| OPA Gatekeeper | https://open-policy-agent.github.io/gatekeeper/ | Policy enforcement |
| Kyverno | https://kyverno.io/docs/ | Alternative to Gatekeeper |
| cert-manager | https://cert-manager.io/docs/ | TLS certificate management |

## Identity

| Resource | URL | Notes |
|----------|-----|-------|
| Keycloak Docs | https://www.keycloak.org/documentation | Identity provider |
| Keycloak Helm Chart | https://www.keycloak.org/server/kubernetes | Official Helm deployment |
| OpenFGA | https://openfga.dev/docs/ | Fine-grained authorization |
| OpenFGA AKS Guide | https://openfga.dev/docs/getting-started/setup-openfga | Setup guide |

## GitOps & Delivery

| Resource | URL | Notes |
|----------|-----|-------|
| ArgoCD | https://argo-cd.readthedocs.io/en/stable/ | GitOps engine |
| ArgoCD App-of-Apps Pattern | https://argo-cd.readthedocs.io/en/stable/operator-manual/cluster-bootstrapping/ | Bootstrap pattern |
| Kong Ingress | https://docs.konghq.com/kubernetes-ingress-controller/ | Ingress controller |

## Observability

| Resource | URL | Notes |
|----------|-----|-------|
| kube-prometheus-stack | https://github.com/prometheus-community/helm-charts/tree/main/charts/kube-prometheus-stack | Prometheus + Grafana |
| Loki Stack | https://grafana.com/docs/loki/latest/setup/install/helm/ | Log aggregation |
| Grafana Tempo | https://grafana.com/docs/tempo/latest/ | Distributed tracing |
| OpenTelemetry Collector | https://opentelemetry.io/docs/collector/ | OTEL collector |

## EventStoreDB

| Resource | URL | Notes |
|----------|-----|-------|
| EventStoreDB | https://developers.eventstore.com/ | Pipeline Ledger backbone |
| EventStoreDB Kubernetes | https://developers.eventstore.com/server/v24.10/installation/kubernetes.html | K8s deployment |
| EventStoreDB .NET Client | https://developers.eventstore.com/clients/dotnet/21.2/ | .NET SDK |

## Temporal.io

| Resource | URL | Notes |
|----------|-----|-------|
| Temporal.io | https://docs.temporal.io/ | Durable workflow engine |
| Temporal Helm Chart | https://github.com/temporalio/helm-charts | Kubernetes deployment |

---

*Phase 01 External References — AI Portal — v1.0*
