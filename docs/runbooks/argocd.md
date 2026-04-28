# ArgoCD Runbook

## Overview
ORBIT uses **ArgoCD 2.12.6** with an **app-of-apps** pattern.  
Namespace: `ai-portal-system` | URL: https://argocd.ai.adports.ae

---

## Access

| Item | Value |
|------|-------|
| UI | https://argocd.ai.adports.ae |
| CLI | `argocd login argocd.ai.adports.ae --sso` |
| Admin password | Vault: `secret/orbit/argocd/admin-password` |

---

## App-of-Apps Structure

```
orbit-infra (AppProject: orbit)
├── orbit-postgres-dev / orbit-postgres-prod
├── orbit-redis-dev / orbit-redis-prod
├── orbit-kafka-dev / orbit-kafka-prod
├── orbit-eventstore-dev / orbit-eventstore-prod
├── orbit-minio-dev / orbit-minio-prod
├── orbit-keycloak-dev / orbit-keycloak-prod
└── orbit-observability-dev / orbit-observability-prod
```

---

## Common Operations

### CLI login
```bash
argocd login argocd.ai.adports.ae --username admin --password $ARGOCD_PASS --grpc-web
```

### List applications
```bash
argocd app list
```

### Sync an application
```bash
argocd app sync orbit-postgres-dev
```

### Force sync (ignore cached state)
```bash
argocd app sync orbit-postgres-dev --force
```

### Check sync status
```bash
argocd app get orbit-postgres-dev
```

### Rollback to previous version
```bash
argocd app history orbit-postgres-dev
argocd app rollback orbit-postgres-dev <revision>
```

### Hard refresh (bypass cache)
```bash
argocd app get orbit-postgres-dev --refresh
```

---

## Adding a New Application

1. Create an `Application` manifest in `src/infrastructure/argocd/apps/<env>/applications.yaml`.
2. Push to `main`. ArgoCD app-of-apps will automatically pick it up and sync.

---

## RBAC

ArgoCD RBAC is mapped to Keycloak groups via OIDC:

| Keycloak Group | ArgoCD Role |
|----------------|-------------|
| `platform-admin` | `role:admin` |
| `platform-dev` | `role:readonly` |

---

## Alerts

| Alert | Meaning | Action |
|-------|---------|--------|
| `ArgoCDAppOutOfSync` | Git drift detected | Run `argocd app sync` or review diff |
| `ArgoCDAppHealthDegraded` | App health check failing | Check pod status of the application |
| `ArgoCDRepoSyncFailed` | Cannot reach GitHub | Check network policies + GitHub connectivity |
