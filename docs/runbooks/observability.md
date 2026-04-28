# Observability Stack Runbook

## Overview
ORBIT observability: **Prometheus + Grafana + Loki + Tempo + OpenTelemetry Collector**  
Namespace: `ai-portal-observability`

---

## Access

| Tool | URL |
|------|-----|
| Grafana | https://grafana.ai.adports.ae |
| Prometheus | https://prometheus.ai.adports.ae |
| AlertManager | https://alertmanager.ai.adports.ae |

---

## Grafana

### Login
SSO via Keycloak (`ai-portal` realm). Members of `platform-admin` group get Admin role.

### Pre-built dashboards
| Dashboard | Purpose |
|-----------|---------|
| Kubernetes / Cluster | Node CPU, memory, pod count |
| Kubernetes / Workloads | Deployment status per namespace |
| ORBIT / API Latency | Portal API P50/P95/P99 latency |
| ORBIT / Pipeline Ledger | Kafka consumer lag, EventStoreDB write rate |
| CloudNativePG | Postgres replication lag, query rate |

### Add a data source (Tempo for traces)
```
Settings → Data Sources → Add → Tempo
URL: http://tempo.ai-portal-observability.svc.cluster.local:3100
```

---

## Prometheus

### Query example (via port-forward)
```bash
kubectl -n ai-portal-observability port-forward svc/kube-prometheus-stack-prometheus 9090:9090 &
curl "http://localhost:9090/api/v1/query?query=kube_pod_status_ready{namespace='ai-portal-core'}" | jq .
```

### Check alert rules
```bash
curl http://localhost:9090/api/v1/rules | jq '.data.groups[].rules[] | select(.state=="firing")'
```

---

## Loki

### Query logs (via Grafana Explore)
```logql
{namespace="ai-portal-core"} |= "ERROR"
{app="portal-api"} | json | level="error" | line_format "{{.message}}"
```

### Query logs via CLI
```bash
kubectl -n ai-portal-observability port-forward svc/loki 3100:3100 &
curl -G "http://localhost:3100/loki/api/v1/query_range" \
  --data-urlencode 'query={namespace="ai-portal-core"}' \
  --data-urlencode 'limit=50' | jq '.data.result[].values'
```

---

## Tempo (Distributed Tracing)

### Search traces via Grafana
Grafana → Explore → Tempo → Search by Service Name or TraceID.

### Verify OTEL Collector is receiving spans
```bash
kubectl -n ai-portal-observability logs -l app.kubernetes.io/name=opentelemetry-collector -f | grep -i "trace"
```

---

## Alerts

| Alert | Meaning | Action |
|-------|---------|--------|
| `PrometheusScrapeFailed` | Target down | Check ServiceMonitor and pod labels |
| `GrafanaDown` | Grafana pod not ready | Check DB (Postgres) and Keycloak |
| `LokiIngestionHigh` | Log rate exceeds limit | Scale Loki replicas or increase limits |
| `TempoHighSpanRate` | Trace volume high | Adjust sampling rate in OTEL Collector |
