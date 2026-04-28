# Instructions — Phase 01: Platform Foundation & Infrastructure

> Add this file to your IDE's custom instructions (Copilot, Cursor, or Claude Code) when working on Phase 01 infrastructure tasks.

---

## Context

You are working on the **AI Portal Platform Infrastructure** — an AKS-based Kubernetes cluster hosting PostgreSQL, Redis, Kafka, EventStoreDB, HashiCorp Vault, Keycloak, Kong Ingress, ArgoCD, and the observability stack (Prometheus, Grafana, Loki, Tempo, OpenTelemetry).

All infrastructure is defined as **Pulumi (TypeScript)** code. All Kubernetes deployments are via **Helm charts** managed by **ArgoCD** (app-of-apps pattern). No `kubectl apply -f` commands directly — everything goes through GitOps.

---

## Coding Standards

### Pulumi (TypeScript)

- Use `@pulumi/azure-native` for all Azure resources (not the legacy `@pulumi/azure`).
- Use `@pulumi/kubernetes` for Kubernetes resources.
- All resource names follow `adports-ai-{component}-{env}` pattern (e.g., `adports-ai-postgres-dev`).
- Use `pulumi.Config` for environment-specific values; never hardcode subscription IDs, resource group names, or tenant IDs.
- Stack references: use `new pulumi.StackReference("org/infra/dev")` when stacks depend on each other.
- Every resource must have `tags: { project: "ai-portal", phase: "01", env: stack.name }`.
- Outputs: export all connection strings, endpoints, and resource IDs as stack outputs (they will be consumed by Phase 02+).

```typescript
// CORRECT pattern
const pgPassword = new random.RandomPassword("pg-password", { length: 32, special: true });
const pgSecret = new vault.kv.SecretV2("postgres/ai-portal-core", {
  mount: "secret",
  name: "postgres/ai-portal-core",
  dataJson: pulumi.jsonStringify({ password: pgPassword.result, host: pgCluster.endpoint }),
});

// WRONG — never export raw secrets as stack outputs
export const postgresPassword = pgPassword.result; // FORBIDDEN
```

### Helm Values

- Every Helm chart's `values.yaml` override file lives in `infrastructure/helm/{chart-name}/values-{env}.yaml`.
- Use Helm `--set` for environment-specific overrides only (never for secrets).
- Secrets are always injected by Vault Agent Injector via pod annotations — never in Helm values files.

### Kubernetes Manifests

- All namespaces declared in `infrastructure/namespaces/namespaces.yaml`.
- All Network Policies live in `infrastructure/network-policies/`.
- Use `PodDisruptionBudget` for all stateful services.
- Resource requests AND limits required on every container.
- Liveness, readiness, and startup probes required on every container.

---

## Security Requirements (Non-Negotiable)

1. **No secrets in Kubernetes Secrets** — all secrets via Vault Agent Injector (`vault.hashicorp.com/agent-inject` annotations).
2. **TLS everywhere** — all service-to-service communication uses TLS. Use cert-manager with the AD Ports internal CA or Let's Encrypt.
3. **Network Policies** — every namespace has a deny-all default; explicit allow rules for required connections only.
4. **Pod Security Standards** — all pods run with `restricted` pod security standard unless documented exception.
5. **Non-root containers** — all containers run as non-root user (UID ≥ 1000).
6. **Read-only root filesystems** where possible.
7. **Resource limits required** — no pod without CPU and memory limits.

---

## ArgoCD GitOps Pattern

```yaml
# infrastructure/argocd/apps/postgres.yaml
apiVersion: argoproj.io/v1alpha1
kind: Application
metadata:
  name: ai-portal-postgres
  namespace: argocd
spec:
  project: ai-portal
  source:
    repoURL: https://gitlab.adports.ae/ai-portal/infra
    targetRevision: main
    path: infrastructure/helm/cloudnativepg
    helm:
      valueFiles:
        - values-prod.yaml
  destination:
    server: https://kubernetes.default.svc
    namespace: ai-portal-data
  syncPolicy:
    automated:
      prune: true
      selfHeal: true
    syncOptions:
      - CreateNamespace=true
```

---

## When Generating Infrastructure Code

- Always generate a corresponding `README.md` in the component folder explaining what the component is, how to access it, how to run smoke tests, and how to rotate credentials.
- Always generate a runbook in `docs/runbooks/{component}.md` covering: startup, shutdown, backup restore, credential rotation, scaling, common failure modes.
- Always generate a Pulumi test in `__tests__/{component}.test.ts`.

---

## What NOT to Do

- Do not use `kubectl apply` directly — all changes go through ArgoCD.
- Do not store passwords or API keys in Pulumi outputs, Git, or Kubernetes Secrets.
- Do not create Azure resources outside of Pulumi — no ClickOps.
- Do not expose services externally without Kong ingress and cert-manager TLS.
- Do not use `latest` image tags — pin to specific digest or semantic version.
- Do not skip resource limits or probes — every container must have both.

---

## Useful Commands for This Phase

```bash
# Preview infra changes without applying
pulumi preview --stack dev

# Apply with confirmation
pulumi up --stack dev

# Check all pods are healthy
kubectl get pods -A | grep -v Running | grep -v Completed

# Port-forward to Keycloak admin
kubectl port-forward svc/keycloak-http 8080:80 -n ai-portal-keycloak

# Port-forward to Grafana
kubectl port-forward svc/prometheus-grafana 3000:80 -n ai-portal-observability

# Check Vault status
kubectl exec -n ai-portal-vault vault-0 -- vault status

# List Kafka topics
kubectl exec -n ai-portal-data kafka-0 -- kafka-topics.sh --list --bootstrap-server localhost:9092
```

---

*Phase 01 Instructions — AI Portal — v1.0*
