# MinIO Runbook

## Overview
ORBIT uses **MinIO** as S3-compatible object storage.  
Namespace: `ai-portal-data` | Dev: standalone | Prod: 4-node distributed.

---

## Access

| Item | Value |
|------|-------|
| Console (UI) | https://minio-console.ai.adports.ae |
| API endpoint (internal) | `http://minio.ai-portal-data.svc.cluster.local:9000` |
| Root credentials | Vault: `secret/orbit/minio/root-creds` |

---

## Buckets

| Bucket | Purpose | Versioning |
|--------|---------|-----------|
| `ai-portal-pg-backups` | CNPG WAL/base backups | Enabled (prod) |
| `ai-portal-artifacts` | Pipeline artifacts, model weights | Off |
| `ai-portal-context-archive` | Archived AI context | Off |

---

## Common Operations

### Check pod status
```bash
kubectl -n ai-portal-data get pods -l app.kubernetes.io/name=minio
```

### MinIO CLI (mc) setup
```bash
# Install mc
curl -O https://dl.min.io/client/mc/release/linux-amd64/mc && chmod +x mc

# Configure
./mc alias set orbit \
  http://minio.ai-portal-data.svc.cluster.local:9000 \
  $MINIO_ROOT_USER $MINIO_ROOT_PASSWORD

# List buckets
./mc ls orbit/
```

### Upload a file
```bash
./mc cp ./my-file.tar.gz orbit/ai-portal-artifacts/
```

### List objects in bucket
```bash
./mc ls orbit/ai-portal-pg-backups/
```

### Check bucket policy
```bash
./mc policy get orbit/ai-portal-artifacts
```

---

## Restore a Postgres backup from MinIO

1. Identify the backup set in `ai-portal-pg-backups`.
2. Create a CNPG recovery cluster (see postgres.md PITR section) referencing the MinIO bucket.

---

## Alerts

| Alert | Meaning | Action |
|-------|---------|--------|
| `MinIODown` | Pod not ready | Check logs: `kubectl -n ai-portal-data logs -l app.kubernetes.io/name=minio` |
| `MinIODiskUsageHigh` | Disk >80% | Add storage or archive old objects |
| `MinIOHealNeeded` | Distributed mode data inconsistency | Run `./mc admin heal orbit` |
