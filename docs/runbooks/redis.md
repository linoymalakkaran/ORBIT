# Redis Cluster Runbook

## Overview
ORBIT uses **Bitnami redis-cluster** Helm chart for session cache and queue.  
Namespace: `ai-portal-data` | Dev: 3 nodes | Prod: 6 nodes (3M+3R)

---

## Connection Details

| Item | Value |
|------|-------|
| Cluster service | `orbit-redis-redis-cluster.ai-portal-data.svc.cluster.local:6379` |
| Auth secret | `orbit-redis-cluster` (Vault-injected, key `redis-password`) |

---

## Common Operations

### Check cluster health
```bash
kubectl -n ai-portal-data exec -it orbit-redis-redis-cluster-0 -- \
  redis-cli -a "$REDIS_PASSWORD" cluster info
```

### List nodes
```bash
kubectl -n ai-portal-data exec -it orbit-redis-redis-cluster-0 -- \
  redis-cli -a "$REDIS_PASSWORD" cluster nodes
```

### Get password from secret
```bash
kubectl -n ai-portal-data get secret orbit-redis-cluster \
  -o jsonpath='{.data.redis-password}' | base64 -d
```

### Flush all data (dev only — destructive)
```bash
# WARNING: only run in dev!
kubectl -n ai-portal-data exec -it orbit-redis-redis-cluster-0 -- \
  redis-cli -a "$REDIS_PASSWORD" flushall
```

### Check memory usage
```bash
kubectl -n ai-portal-data exec -it orbit-redis-redis-cluster-0 -- \
  redis-cli -a "$REDIS_PASSWORD" info memory | grep used_memory_human
```

---

## Scaling

To add more nodes, update the Helm values `cluster.nodes` and run:
```bash
helm upgrade orbit-redis bitnami/redis-cluster \
  -n ai-portal-data -f src/infrastructure/helm/redis/values-prod.yaml
```

---

## Alerts

| Alert | Meaning | Action |
|-------|---------|--------|
| `RedisClusterDown` | Majority of masters unavailable | Check pod status, restart pods |
| `RedisHighMemory` | Memory >80% of limit | Increase memory limit or evict keys |
| `RedisConnectionRefused` | Pod not ready | Check liveness probe, describe pod |
