# EventStoreDB Runbook

## Overview
ORBIT uses **EventStoreDB 24.10.1** as an append-only pipeline ledger.  
Namespace: `ai-portal-data` | Dev: single node | Prod: 3-node cluster.

---

## Connection Details

| Item | Value |
|------|-------|
| HTTP/gRPC (internal) | `eventstore.ai-portal-data.svc.cluster.local:2113` |
| TCP (legacy) | `eventstore.ai-portal-data.svc.cluster.local:1113` |
| Admin UI | https://eventstore.ai.adports.ae (via Kong Ingress) |

---

## Common Operations

### Check pod status
```bash
kubectl -n ai-portal-data get pods -l app.kubernetes.io/name=eventstore
```

### View live logs
```bash
kubectl -n ai-portal-data logs -l app.kubernetes.io/name=eventstore -f
```

### List streams (HTTP API)
```bash
kubectl -n ai-portal-data port-forward svc/eventstore 2113:2113 &
curl -s http://localhost:2113/streams?count=20 \
  -u admin:$ESDB_PASS | jq '.entries[].title'
```

### Read a stream
```bash
curl -s "http://localhost:2113/streams/portal-ledger-events?count=10" \
  -H "Accept: application/json" -u admin:$ESDB_PASS | jq .
```

### Append an event (debug/test only)
```bash
curl -s -X POST http://localhost:2113/streams/portal-test \
  -H "Content-Type: application/vnd.eventstore.events+json" \
  -u admin:$ESDB_PASS \
  -d '[{"eventId":"'"$(uuidgen)"'","eventType":"TestEvent","data":{"hello":"world"}}]'
```

---

## Cluster Health (Prod)

```bash
# Check cluster gossip
kubectl -n ai-portal-data exec -it eventstore-0 -- \
  curl -s http://localhost:2113/gossip | jq '.members[] | {state, isAlive}'
```

Expected: one `Leader` + two `Follower` nodes, all `isAlive: true`.

---

## Backup / Restore

EventStoreDB supports chunk file backups. For prod, use the snapshot approach:
1. Quiesce writes via application config flag.
2. Copy `/var/lib/eventstore/data` from the Leader pod to MinIO.
3. Re-enable writes.

> Full online backup via the EventStore Backup & Restore plugin is recommended for prod.

---

## Alerts

| Alert | Meaning | Action |
|-------|---------|--------|
| `EventStoreDown` | Pod not ready | Check logs, describe pod |
| `EventStoreHighDiskUsage` | Disk >80% | Increase PVC or enable scavenging |
| `EventStoreLeaderElection` | Leader changed | Normal — check if old leader crashed |
