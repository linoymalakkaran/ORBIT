# ORBIT Platform — Operational Runbook

## Prerequisites

- `kubectl` configured against TKG cluster
- `argocd` CLI installed
- Access to Vault (`vault login`)
- Harbor credentials

---

## 1. Deploying a New Service Version

```bash
# Update image tag in service k8s/deployment.yaml
# Commit and push to main
git add src/<service>/k8s/deployment.yaml
git commit -m "chore: bump <service> to v1.x.x"
git push origin main
# ArgoCD auto-syncs within ~3 minutes
argocd app sync orbit-<service>   # force immediate sync
```

---

## 2. Rolling Back a Service

```bash
# Via ArgoCD UI: Apps → orbit-<service> → History → select revision → Rollback

# Via CLI:
argocd app rollback orbit-portal-api <revision-number>
```

---

## 3. Checking Pipeline Ledger Chain Integrity

```bash
kubectl exec -n ai-portal deploy/pipeline-ledger -- \
  curl -s http://localhost:8000/api/ledger/verify?project_id=<project_id>
```

Expected: `{"chain_valid": true, "entry_count": N}`

---

## 4. Vault Secret Rotation

```bash
# Rotate a secret
vault kv put secret/<service>/env key=new_value

# Restart pods to pick up new vault-injected secrets
kubectl rollout restart deployment/<service> -n ai-portal
```

---

## 5. Scaling Services

```bash
kubectl scale deployment <service> --replicas=3 -n ai-portal
# Or update replicaCount in k8s/deployment.yaml and commit
```

---

## 6. Kafka Topic Lag Monitoring

```bash
kubectl exec -n kafka orbit-kafka-kafka-0 -- \
  bin/kafka-consumer-groups.sh --bootstrap-server localhost:9092 \
  --describe --all-groups
```

---

## 7. Common Troubleshooting

| Symptom | Action |
|---|---|
| Pod in `CrashLoopBackOff` | `kubectl logs <pod> -n ai-portal --previous` |
| Vault secret not injected | Check `vault.hashicorp.com/agent-inject: "true"` annotation; check SA binding |
| ArgoCD app `OutOfSync` | `argocd app sync orbit-<service>` |
| LiteLLM 429 errors | Check Azure OpenAI quota; scale LiteLLM replicas |
| Ledger chain broken | Check for missing `previous_hash` in ESDB stream; re-run projector |
| Temporal workflow stuck | Open Temporal UI → find workflow → terminate and re-trigger |

---

## 8. Monitoring Dashboards

| Dashboard | URL |
|---|---|
| Grafana | `https://grafana.ai.adports.ae` |
| ORBIT Services | Grafana → ORBIT folder |
| Kafka | Grafana → Kafka folder |
| Temporal | `https://temporal.ai.adports.ae` |
| ArgoCD | `https://argocd.ai.adports.ae` |

---

## 9. Backup Procedures

```bash
# PostgreSQL backup
kubectl exec -n ai-portal-data deploy/postgresql -- \
  pg_dumpall -U postgres > backup-$(date +%Y%m%d).sql

# EventStoreDB backup
# ESDB replication handles HA; for cold backup:
kubectl exec -n ai-portal-data eventstore-0 -- \
  tar cz /var/lib/eventstore/data > esdb-backup-$(date +%Y%m%d).tar.gz

# MinIO backup
mc mirror minio/orbit-data local-backup/
```

---

## 10. Incident Response

1. **Identify** — check Grafana alerts + Loki logs for error spikes
2. **Isolate** — scale down affected service if causing cascading failures
3. **Mitigate** — rollback via ArgoCD if regression
4. **Communicate** — update Jira incident ticket
5. **Post-mortem** — create ADR for root cause + remediation steps
