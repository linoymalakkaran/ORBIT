# PostgreSQL (CloudNativePG) Runbook

## Overview
ORBIT uses **CloudNativePG** operator to manage a PostgreSQL cluster named `orbit-postgres` in namespace `ai-portal-data`. Three databases are provisioned: `ai_portal_core`, `ai_portal_keycloak`, `ai_portal_context`.

---

## Connection Details

| Item | Value |
|------|-------|
| Primary service | `orbit-postgres-<env>-rw.ai-portal-data.svc.cluster.local:5432` |
| Read-only service | `orbit-postgres-<env>-ro.ai-portal-data.svc.cluster.local:5432` |
| Credentials secret | `orbit-pg-superuser-creds` (Vault-injected) |
| Backup bucket | `s3://ai-portal-pg-backups` (MinIO) |

---

## Common Operations

### Check cluster health
```bash
kubectl -n ai-portal-data get cluster orbit-postgres-<env>
kubectl -n ai-portal-data describe cluster orbit-postgres-<env>
```

### List pods
```bash
kubectl -n ai-portal-data get pods -l cnpg.io/cluster=orbit-postgres-<env>
```

### Connect to primary (read/write)
```bash
kubectl -n ai-portal-data exec -it \
  $(kubectl -n ai-portal-data get pod -l cnpg.io/instanceRole=primary -o name | head -1) \
  -- psql -U orbit_admin -d ai_portal_core
```

### Trigger immediate backup
```bash
kubectl -n ai-portal-data apply -f - <<EOF
apiVersion: postgresql.cnpg.io/v1
kind: Backup
metadata:
  name: manual-backup-$(date +%Y%m%d%H%M)
  namespace: ai-portal-data
spec:
  method: barmanObjectStore
  cluster:
    name: orbit-postgres-<env>
EOF
```

### Check backup status
```bash
kubectl -n ai-portal-data get backup
```

### Promote standby to primary (emergency failover)
```bash
# CloudNativePG handles failover automatically.
# Manual promotion (use only if operator is unavailable):
kubectl -n ai-portal-data annotate cluster orbit-postgres-<env> \
  cnpg.io/reloadConfig="true"
```

---

## Point-in-Time Recovery (PITR)

```bash
kubectl -n ai-portal-data apply -f - <<EOF
apiVersion: postgresql.cnpg.io/v1
kind: Cluster
metadata:
  name: orbit-postgres-pitr
  namespace: ai-portal-data
spec:
  instances: 1
  bootstrap:
    recovery:
      backup:
        name: <backup-name>
      recoveryTarget:
        targetTime: "2024-12-01 12:00:00"
  storage:
    size: 50Gi
EOF
```

---

## Alerts

| Alert | Meaning | Action |
|-------|---------|--------|
| `CnpgClusterNotHealthy` | Cluster status != Ready | Check pod logs, describe cluster |
| `CnpgBackupFailed` | Backup job failed | Check MinIO connectivity + Vault creds |
| `CnpgHighConnections` | >80% connection limit | Scale Pooler or increase `max_connections` |

---

## Scaling

Edit the cluster CR to increase replicas:
```bash
kubectl -n ai-portal-data patch cluster orbit-postgres-<env> \
  --type merge -p '{"spec":{"instances":3}}'
```
