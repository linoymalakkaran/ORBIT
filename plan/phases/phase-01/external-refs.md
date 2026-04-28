# Phase 01 — External References

## VMware Tanzu (Primary Platform)

| Resource | URL | Notes |
|----------|-----|-------|
| TKG 2.x Documentation | https://docs.vmware.com/en/VMware-Tanzu-Kubernetes-Grid/2.5/tkg-deploy-mc/GUID-index.html | Start here for cluster design |
| TKG Management Cluster | https://docs.vmware.com/en/VMware-Tanzu-Kubernetes-Grid/2.5/tkg-deploy-mc/GUID-mgmt-clusters-index.html | Management cluster setup |
| TKG Workload Clusters | https://docs.vmware.com/en/VMware-Tanzu-Kubernetes-Grid/2.5/using-tkg/workload-clusters-index.html | Workload cluster provisioning |
| vSphere with Tanzu | https://docs.vmware.com/en/VMware-vSphere/8.0/vsphere-with-tanzu-getting-started/GUID-index.html | Alternative: supervisor-based |
| Antrea CNI | https://antrea.io/docs/ | Default CNI for TKG |
| MetalLB | https://metallb.universe.tf/configuration/ | On-prem LoadBalancer |
| Harbor Registry | https://goharbor.io/docs/ | On-prem OCI registry |
| Pulumi vSphere Provider | https://www.pulumi.com/registry/packages/vsphere/ | Pulumi IaC for vSphere |
| Pulumi Kubernetes Provider | https://www.pulumi.com/registry/packages/kubernetes/ | Pulumi K8s resources |
| CIS Kubernetes Benchmark | https://www.cisecurity.org/benchmark/kubernetes | Security baseline (kube-bench) |
| kube-bench | https://github.com/aquasecurity/kube-bench | CIS benchmark scanner |
| Tanzu Mission Control | https://docs.vmware.com/en/VMware-Tanzu-Mission-Control/ | Cluster lifecycle management |

## Future: AKS (Provider Swap)

| Resource | URL | Notes |
|----------|-----|-------|
| AKS Best Practices | https://learn.microsoft.com/en-us/azure/aks/best-practices | AKS cluster design |
| Pulumi Azure Native | https://www.pulumi.com/registry/packages/azure-native/ | AKS stack IaC docs |
| AKS Workload Identity | https://learn.microsoft.com/en-us/azure/aks/workload-identity-overview | AKS-specific identity |

## Databases & Storage

| Resource | URL | Notes |
|----------|-----|-------|
| CloudNativePG | https://cloudnative-pg.io/documentation/ | Postgres operator |
| CloudNativePG High Availability | https://cloudnative-pg.io/documentation/current/replication/ | HA setup guide |
| PgBouncer Config | https://www.pgbouncer.org/config.html | Connection pooler |
| Redis Cluster Tutorial | https://redis.io/docs/management/scaling/ | Cluster mode setup |
| Strimzi Kafka | https://strimzi.io/documentation/ | Kafka on Kubernetes |
| MinIO Operator | https://min.io/docs/minio/kubernetes/upstream/ | On-prem S3 storage operator |
| MinIO CNPG Backup | https://cloudnative-pg.io/documentation/current/backup_recovery/ | CNPG backup to S3/MinIO |

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
| OpenFGA Kubernetes Guide | https://openfga.dev/docs/getting-started/setup-openfga | Setup guide |

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
