"""Service Health Monitor (Gate 2) — AI-powered monitoring with anomaly detection,
alert correlation, auto-remediation proposals, and runbook generation."""
from __future__ import annotations

import asyncio
import logging
import time
from datetime import datetime, timezone
from typing import Optional

import httpx
import litellm
from fastapi import FastAPI, BackgroundTasks
from opentelemetry.instrumentation.fastapi import FastAPIInstrumentor
from pydantic import BaseModel, Field
from pydantic_settings import BaseSettings, SettingsConfigDict

logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO)


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_prefix="HEALTHMON_", env_file=".env", extra="ignore")
    prometheus_url: str = "http://prometheus-operated.monitoring.svc:9090"
    loki_url: str = "http://loki.monitoring.svc:3100"
    registry_url: str = "http://project-registry.ai-portal.svc:80"
    orchestrator_url: str = "http://orchestrator.ai-portal.svc:80"
    ledger_url: str = "http://pipeline-ledger.ai-portal.svc:80"
    litellm_api_base: str = "http://litellm-gateway.litellm.svc:4000"
    litellm_api_key: str = "changeme"
    default_model: str = "gpt-4o-mini"
    poll_interval_seconds: int = 60
    anomaly_threshold_p99_ms: int = 2000    # Alert if p99 > 2s
    error_rate_alert_pct: float = 5.0       # Alert if error rate > 5%


settings = Settings()
litellm.api_base = settings.litellm_api_base
litellm.api_key = settings.litellm_api_key


# ── Prometheus Queries ────────────────────────────────────────────────────────

async def query_prometheus(promql: str) -> list[dict]:
    """Execute a PromQL instant query."""
    async with httpx.AsyncClient(timeout=10) as client:
        resp = await client.get(f"{settings.prometheus_url}/api/v1/query", params={"query": promql})
        if resp.status_code != 200:
            return []
        data = resp.json()
        return data.get("result", [])


async def get_service_error_rates(namespace: str = "ai-portal") -> list[dict]:
    """Get HTTP error rates per service."""
    promql = f"""
        sum by (service) (
          rate(http_requests_total{{namespace="{namespace}", status_code=~"5.."}}[5m])
        ) /
        sum by (service) (
          rate(http_requests_total{{namespace="{namespace}"}}[5m])
        ) * 100
    """
    results = await query_prometheus(promql)
    return [
        {
            "service": r["metric"].get("service", "unknown"),
            "error_rate_pct": float(r["value"][1]),
            "timestamp": r["value"][0],
        }
        for r in results
    ]


async def get_service_p99_latencies(namespace: str = "ai-portal") -> list[dict]:
    """Get P99 latency per service."""
    promql = f"""
        histogram_quantile(0.99,
          sum by (service, le) (
            rate(http_request_duration_seconds_bucket{{namespace="{namespace}"}}[5m])
          )
        ) * 1000
    """
    results = await query_prometheus(promql)
    return [
        {
            "service": r["metric"].get("service", "unknown"),
            "p99_ms": float(r["value"][1]),
            "timestamp": r["value"][0],
        }
        for r in results
    ]


# ── Log Anomaly Detection ─────────────────────────────────────────────────────

async def get_error_logs(service: str, minutes: int = 10) -> list[str]:
    """Fetch recent error logs from Loki."""
    query = f'{{app="{service}", namespace="ai-portal"}} |= "ERROR" | line_format "{{{{.msg}}}}"'
    end = int(time.time() * 1e9)
    start = end - (minutes * 60 * int(1e9))
    async with httpx.AsyncClient(timeout=10) as client:
        resp = await client.get(f"{settings.loki_url}/loki/api/v1/query_range", params={
            "query": query, "start": start, "end": end, "limit": 50,
        })
        if resp.status_code != 200:
            return []
        streams = resp.json().get("data", {}).get("result", [])
        lines = []
        for stream in streams:
            for _, line in stream.get("values", []):
                lines.append(line)
        return lines[:20]  # Return up to 20 error lines


# ── LLM Analysis ─────────────────────────────────────────────────────────────

async def _llm(prompt: str) -> str:
    r = await litellm.acompletion(
        model=settings.default_model,
        messages=[
            {"role": "system", "content": "You are an SRE expert analyzing service health issues."},
            {"role": "user", "content": prompt},
        ],
        temperature=0.1,
        max_tokens=500,
    )
    return r.choices[0].message.content or ""


async def correlate_alerts_and_propose_remediation(
    service: str,
    error_rate: float,
    p99_ms: float,
    error_logs: list[str],
) -> dict:
    """Use LLM to correlate alerts and generate a remediation work package."""
    logs_excerpt = "\n".join(error_logs[:10]) if error_logs else "No recent error logs"
    prompt = f"""Service '{service}' has health issues:
- Error rate: {error_rate:.1f}% (threshold: {settings.error_rate_alert_pct}%)
- P99 latency: {p99_ms:.0f}ms (threshold: {settings.anomaly_threshold_p99_ms}ms)
- Recent error logs:
{logs_excerpt}

Provide:
1. Root cause hypothesis (2-3 sentences)
2. Immediate remediation steps (numbered list)
3. Long-term fix recommendation
4. Severity: CRITICAL | HIGH | MEDIUM

Format as JSON: {{"root_cause": "...", "remediation_steps": [...], "long_term_fix": "...", "severity": "..."}}"""
    analysis = await _llm(prompt)
    try:
        import json, re
        m = re.search(r"\{.*\}", analysis, re.DOTALL)
        return json.loads(m.group(0)) if m else {"root_cause": analysis, "remediation_steps": [], "long_term_fix": "", "severity": "MEDIUM"}
    except Exception:
        return {"root_cause": analysis, "remediation_steps": [], "long_term_fix": "", "severity": "MEDIUM"}


async def generate_runbook(service: str, issue_description: str) -> str:
    """Generate an operational runbook for a service issue."""
    prompt = f"""Generate an operational runbook for service '{service}' for issue:
{issue_description}

Include sections:
1. Prerequisites
2. Immediate response steps
3. Investigation commands (kubectl, curl, logs)
4. Resolution procedures
5. Rollback procedure
6. Post-incident checklist

Use markdown format."""
    return await _llm(prompt)


# ── Background Monitor ────────────────────────────────────────────────────────

_monitoring_task: asyncio.Task | None = None
_alerts: list[dict] = []


async def _monitor_loop():
    """Background task: poll metrics every N seconds and generate alerts."""
    while True:
        try:
            error_rates = await get_service_error_rates()
            latencies = await get_service_p99_latencies()

            # Map latencies by service
            latency_map = {l["service"]: l["p99_ms"] for l in latencies}

            for service_metric in error_rates:
                svc = service_metric["service"]
                error_rate = service_metric["error_rate_pct"]
                p99 = latency_map.get(svc, 0.0)

                if error_rate > settings.error_rate_alert_pct or p99 > settings.anomaly_threshold_p99_ms:
                    # Fetch logs and analyze
                    logs = await get_error_logs(svc)
                    analysis = await correlate_alerts_and_propose_remediation(svc, error_rate, p99, logs)

                    alert = {
                        "service": svc,
                        "error_rate_pct": error_rate,
                        "p99_ms": p99,
                        "severity": analysis.get("severity", "MEDIUM"),
                        "root_cause": analysis.get("root_cause", ""),
                        "remediation_steps": analysis.get("remediation_steps", []),
                        "timestamp": datetime.now(timezone.utc).isoformat(),
                    }
                    _alerts.append(alert)
                    _alerts[:] = _alerts[-100:]  # keep last 100

                    # Push to orchestrator as auto-remediation work package
                    try:
                        async with httpx.AsyncClient(timeout=5) as client:
                            await client.post(f"{settings.orchestrator_url}/api/pipelines", json={
                                "project_id": svc,
                                "intent": f"Auto-remediation: {analysis.get('root_cause', 'unknown issue')}",
                                "triggered_by": "health-monitor",
                                "metadata": alert,
                            })
                    except Exception:
                        pass

                    logger.warning("Alert: service=%s error_rate=%.1f%% p99=%.0fms", svc, error_rate, p99)

        except Exception as e:
            logger.error("Monitor loop error: %s", e)

        await asyncio.sleep(settings.poll_interval_seconds)


# ── FastAPI ──────────────────────────────────────────────────────────────────

app = FastAPI(title="ORBIT Service Health Monitor", version="2.0.0")
FastAPIInstrumentor.instrument_app(app)


@app.on_event("startup")
async def startup():
    global _monitoring_task
    _monitoring_task = asyncio.create_task(_monitor_loop())


@app.on_event("shutdown")
async def shutdown():
    if _monitoring_task:
        _monitoring_task.cancel()


class ManualCheckRequest(BaseModel):
    service: str
    namespace: str = "ai-portal"


@app.post("/api/health/check")
async def manual_health_check(req: ManualCheckRequest):
    """Manually trigger health check for a specific service."""
    error_rates = await get_service_error_rates(req.namespace)
    latencies = await get_service_p99_latencies(req.namespace)

    svc_error = next((e for e in error_rates if e["service"] == req.service), {"error_rate_pct": 0})
    svc_latency = next((l for l in latencies if l["service"] == req.service), {"p99_ms": 0})

    error_rate = svc_error["error_rate_pct"]
    p99_ms = svc_latency["p99_ms"]
    logs = await get_error_logs(req.service)

    health = "healthy"
    if error_rate > settings.error_rate_alert_pct or p99_ms > settings.anomaly_threshold_p99_ms:
        health = "degraded"
        analysis = await correlate_alerts_and_propose_remediation(req.service, error_rate, p99_ms, logs)
    else:
        analysis = {}

    return {
        "service": req.service,
        "health_status": health,
        "metrics": {"error_rate_pct": error_rate, "p99_ms": p99_ms},
        "analysis": analysis,
        "checked_at": datetime.now(timezone.utc).isoformat(),
    }


@app.get("/api/health/alerts")
async def get_alerts(limit: int = 50, severity: Optional[str] = None):
    """Get recent health alerts."""
    filtered = _alerts
    if severity:
        filtered = [a for a in _alerts if a.get("severity") == severity.upper()]
    return {"alerts": filtered[-limit:], "total": len(filtered)}


@app.post("/api/health/runbook")
async def request_runbook(service: str, issue_description: str):
    """Generate an operational runbook for a service issue."""
    runbook = await generate_runbook(service, issue_description)
    return {"service": service, "runbook": runbook}


@app.get("/health/live")
async def liveness():
    return {"status": "ok"}


@app.get("/health/ready")
async def readiness():
    try:
        async with httpx.AsyncClient(timeout=3) as client:
            resp = await client.get(f"{settings.prometheus_url}/-/healthy")
            prometheus_ok = resp.status_code == 200
    except Exception:
        prometheus_ok = False
    return {"status": "ok", "prometheus": "ok" if prometheus_ok else "degraded"}
