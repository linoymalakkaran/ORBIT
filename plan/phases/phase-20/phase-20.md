# Phase 20 — Service Health Monitor (Gate 2 Checkpoint)

## Summary

Implement the **Service Health Monitor** — a proactive, AI-powered monitoring system that continuously watches all registered services, detects anomalies, correlates alerts across the stack (infrastructure, application, business metrics), and automatically opens remediation work packages in the Portal. This is the **Gate 2 checkpoint** — after this phase, the platform has a full "build + monitor" loop for any project.

---

## Objectives

1. Implement metrics collection pipeline (AKS → Prometheus → anomaly detector).
2. Implement log analysis pipeline (Loki → log anomaly scorer).
3. Implement trace anomaly detection (Tempo → high-latency span detector).
4. Implement business metrics monitoring (KPI deviation alerts from Postgres).
5. Implement alert correlation engine (link infrastructure + app + business alerts).
6. Implement auto-remediation proposal (generate work package when alert triggers).
7. Implement notification routing (Portal notification + Slack/email/Teams).
8. Implement health dashboard in Portal.
9. Implement runbook generator (auto-generate runbook for each service).
10. Conduct Gate 2 validation.

---

## Prerequisites

- Phase 01 (Prometheus + Grafana + Loki + Tempo deployed).
- Phase 19 (Project Registry — knows which services to monitor).
- Phase 10 (Orchestrator — receives auto-remediation work packages).
- Phase 05 (Pipeline Ledger — health events recorded as compliance evidence).

---

## Duration

**3 weeks** (last week = Gate 2 validation)

**Squad:** Platform Squad + Governance Squad (1 SRE + 1 Python/AI + 1 Angular)

---

## Deliverables

| # | Deliverable | Acceptance Criterion |
|---|------------|---------------------|
| D1 | Metrics anomaly detector | Detects CPU spike > 3σ and generates alert |
| D2 | Log anomaly scorer | Detects ERROR/FATAL rate increase > baseline |
| D3 | Trace anomaly detector | Detects p99 latency increase > 20% from rolling baseline |
| D4 | Business metrics monitor | P0 KPI deviation detected and alerted |
| D5 | Alert correlation | Infrastructure + app + business alerts grouped per service incident |
| D6 | Auto-remediation proposal | Correlated alert → work package opened in Portal within 5 minutes |
| D7 | Notification routing | Architect and on-call engineer notified via Portal + configured channels |
| D8 | Health dashboard | All registered services visible with health status + SLO indicator |
| D9 | Runbook generator | Runbook generated for each service at deploy time |
| D10 | Gate 2 validation | Full Gate 2 checklist passes |

---

## Metrics Anomaly Detector

```python
# health_monitor/metrics_anomaly_detector.py
class MetricsAnomalyDetector:
    """
    Uses rolling z-score to detect anomalies in Prometheus metrics.
    Window: 7 days of hourly data.
    Alert threshold: z-score > 3.0.
    """

    async def check_service(self, service: Service) -> list[MetricsAlert]:
        alerts = []
        metrics_to_watch = [
            ("container_cpu_usage_seconds_total", "CPU"),
            ("container_memory_working_set_bytes", "Memory"),
            ("http_request_duration_seconds", "Request latency"),
            ("http_requests_total{status=~'5..'}", "Error rate"),
        ]

        for metric_query, label in metrics_to_watch:
            # Fetch last 7 days of hourly data
            history = await prometheus.query_range(
                query=f'{metric_query}{{namespace="{service.aks_namespace}", deployment="{service.aks_deployment}"}}',
                start=datetime.utcnow() - timedelta(days=7),
                end=datetime.utcnow(),
                step="1h"
            )

            current_value = history[-1].value
            baseline = statistics.mean(h.value for h in history[:-1])
            std_dev = statistics.stdev(h.value for h in history[:-1])

            if std_dev > 0:
                z_score = (current_value - baseline) / std_dev
                if abs(z_score) > 3.0:
                    alerts.append(MetricsAlert(
                        service_id=service.id,
                        metric=label,
                        current_value=current_value,
                        baseline=baseline,
                        z_score=z_score,
                        severity="HIGH" if abs(z_score) > 5.0 else "MEDIUM"
                    ))

        return alerts
```

---

## Alert Correlation Engine

```python
# health_monitor/alert_correlator.py
class AlertCorrelator:
    """
    Groups alerts from different sources (metrics/logs/traces/business)
    into a single ServiceIncident if they occur within a 15-minute window
    for the same service.
    """

    CORRELATION_WINDOW = timedelta(minutes=15)

    async def correlate(self, alerts: list[BaseAlert]) -> list[ServiceIncident]:
        incidents = []
        by_service: dict[str, list[BaseAlert]] = defaultdict(list)

        for alert in alerts:
            by_service[alert.service_id].append(alert)

        for service_id, service_alerts in by_service.items():
            if len(service_alerts) >= 2:
                # Multiple alert types for the same service = likely incident
                root_cause = await self._infer_root_cause(service_id, service_alerts)
                incidents.append(ServiceIncident(
                    service_id=service_id,
                    alerts=service_alerts,
                    severity=max(a.severity for a in service_alerts),
                    root_cause_hypothesis=root_cause,
                    remediation_suggestions=await self._suggest_remediation(root_cause)
                ))

        return incidents

    async def _infer_root_cause(self, service_id: str, alerts: list[BaseAlert]) -> str:
        """Use LLM to synthesize root cause from correlated alerts."""
        alert_summary = "\n".join(str(a) for a in alerts)
        recent_deployments = await registry_db.get_recent_deployments(service_id, hours=24)

        prompt = f"""
Service {service_id} has triggered multiple alerts:
{alert_summary}

Recent deployments in last 24h:
{recent_deployments}

What is the most likely root cause? Be concise (1-2 sentences).
"""
        # Use economy tier (DeepSeek) for this diagnostic task
        return await llm_gateway.complete(prompt, tier="economy")
```

---

## Auto-Remediation Work Package

When a `ServiceIncident` is created, the Health Monitor opens a work package in the Portal:

```python
async def create_remediation_work_package(incident: ServiceIncident) -> WorkPackage:
    """
    Creates a Portal work package to address the incident.
    Follows the Hook Engine to ensure proper approval gates.
    """
    wp = WorkPackage(
        type="incident-remediation",
        title=f"[INCIDENT] {incident.service.name} — {incident.root_cause_hypothesis[:80]}",
        priority="P1" if incident.severity == "HIGH" else "P2",
        service_id=incident.service_id,
        alerts=incident.alerts,
        remediation_suggestions=incident.remediation_suggestions,
        auto_approve=False,  # Always requires architect review for production
    )

    await portal_api.create_work_package(wp)
    await notifications.send_to_on_call(
        f"P{wp.priority} incident on {incident.service.name}. Work package {wp.id} created."
    )
    await ledger.record(IncidentCreatedEvent(incident_id=incident.id, work_package_id=wp.id))
    return wp
```

---

## Generated Runbook

At service deploy time, the Health Monitor generates a runbook for each service:

```markdown
# Runbook: DGD Declaration Service

## Overview
- **Service**: dgd-declaration-service
- **Namespace**: dgd-prod
- **Team**: DGD Squad
- **On-Call Slack**: #dgd-on-call

## Health Checks
- **Liveness**: GET https://api.adports.ae/dgd/health/live → 200 OK
- **Readiness**: GET https://api.adports.ae/dgd/health/ready → 200 OK

## SLOs
- Availability: 99.9% (< 8.7h downtime/year)
- Latency p99: < 2s for POST /declarations
- Error rate: < 0.1% of requests

## Common Issues

### High CPU Usage
**Detection**: CPU > 80% for 5 minutes
**Diagnosis**: Check for runaway background jobs or N+1 queries
**Resolution**: `kubectl rollout restart deployment/dgd-declaration-service -n dgd-prod`

### Database Connection Exhaustion
**Detection**: Error rate spike + `connection refused` in logs
**Diagnosis**: `kubectl exec ... -- psql -c "SELECT count(*), state FROM pg_stat_activity GROUP BY state;"`
**Resolution**: Increase connection pool size in Helm values or restart pod

## Emergency Contacts
- Primary: DGD Squad Lead
- Secondary: Platform Team (via Portal incident page)
```

---

## Gate 2 Criteria

Gate 2 validates that the platform runs an autonomous build-and-monitor loop:

| # | Criterion | Measurement |
|---|-----------|------------|
| G2.1 | 3+ completed projects in the system (DGD pilot + 2 more) | Registry service count |
| G2.2 | Health monitor detects injected CPU spike within 3 minutes | Chaos test with `kubectl top` |
| G2.3 | Correlated incident auto-creates work package in Portal | Work package visible in Portal |
| G2.4 | On-call engineer notified within 5 minutes of incident | Notification timestamp log |
| G2.5 | Service Health Monitor dashboard shows all 3 projects with SLO indicators | UI screenshot |
| G2.6 | Runbook available for every deployed service | Registry runbook URL check |
| G2.7 | 100% of generated code passed security scans | Ledger scan result records |
| G2.8 | Pipeline Ledger chain integrity intact (0 tamper events) | Tamper-detection check |
| G2.9 | Gate 1 criteria still passing (regression check) | Automated regression run |
| G2.10 | Azure monthly cost < $3,000 for full platform | Azure Cost Management |

---

## Step-by-Step Execution Plan

### Week 1: Anomaly Detection

- [ ] Implement `MetricsAnomalyDetector` (z-score, 7-day rolling window).
- [ ] Implement `LogAnomalyScorer` (ERROR/FATAL rate from Loki).
- [ ] Implement `TraceAnomalyDetector` (p99 latency from Tempo).
- [ ] Test: inject CPU spike via stress container; alert fires within 3 minutes.

### Week 2: Correlation + Remediation + Runbooks

- [ ] Implement `AlertCorrelator` (15-minute window grouping).
- [ ] Implement root cause inference (LLM synthesis from correlated alerts).
- [ ] Implement auto-remediation work package creation.
- [ ] Implement notification routing (Portal + Slack/email/Teams).
- [ ] Implement runbook generator.

### Week 3: Dashboard + Gate 2

- [ ] Implement health dashboard (service list + SLO indicators + incident timeline).
- [ ] Implement health status in Registry UI (links to health dashboard per service).
- [ ] Run Gate 2 validation checklist.
- [ ] Fix any issues found.
- [ ] Record Gate 2 pass/fail in Pipeline Ledger with signed approvals.

---

*Phase 20 — Service Health Monitor (Gate 2 Checkpoint) — AI Portal — v1.0*
