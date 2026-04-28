"""Platform Health Monitor Agent — polls K8s workloads + emits alerts to Kafka."""
from __future__ import annotations

import asyncio
import json
import logging
import subprocess
from typing import Any

import httpx
from confluent_kafka import Producer
from fastapi import FastAPI
from opentelemetry.instrumentation.fastapi import FastAPIInstrumentor
from pydantic_settings import BaseSettings, SettingsConfigDict

logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO)


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_prefix="HEALTH_", env_file=".env", extra="ignore")
    kafka_bootstrap_servers: str = "kafka:9092"
    kafka_topic_alerts: str = "orbit.health.alerts"
    poll_interval_seconds: int = 60
    namespaces: str = "ai-portal,ai-portal-data,monitoring"


settings = Settings()
_producer = Producer({"bootstrap.servers": settings.kafka_bootstrap_servers})

app = FastAPI(title="ORBIT Health Monitor", version="1.0.0")
FastAPIInstrumentor.instrument_app(app)

_UNHEALTHY_STATUSES: set = {"CrashLoopBackOff", "Error", "OOMKilled", "ImagePullBackOff"}


def _check_namespace(ns: str) -> list[dict]:
    try:
        result = subprocess.run(
            ["kubectl", "get", "pods", "-n", ns, "-o", "json"],
            capture_output=True, text=True, timeout=10
        )
        pods = json.loads(result.stdout).get("items", [])
    except Exception:
        return []

    issues = []
    for pod in pods:
        statuses = pod.get("status", {}).get("containerStatuses", [])
        for cs in statuses:
            waiting = cs.get("state", {}).get("waiting", {})
            reason = waiting.get("reason", "")
            if reason in _UNHEALTHY_STATUSES:
                issues.append({
                    "namespace": ns,
                    "pod": pod["metadata"]["name"],
                    "container": cs["name"],
                    "reason": reason,
                })
    return issues


async def _monitor_loop():
    while True:
        all_issues = []
        for ns in settings.namespaces.split(","):
            all_issues.extend(_check_namespace(ns.strip()))

        if all_issues:
            for issue in all_issues:
                _producer.produce(
                    settings.kafka_topic_alerts,
                    key=issue["namespace"].encode(),
                    value=json.dumps({"type": "pod_unhealthy", "data": issue}).encode(),
                )
            _producer.poll(0)
            logger.warning("Health issues detected: %d", len(all_issues))
        else:
            logger.info("All pods healthy across %s", settings.namespaces)

        await asyncio.sleep(settings.poll_interval_seconds)


@app.on_event("startup")
async def startup():
    asyncio.create_task(_monitor_loop())


@app.get("/health/live")
async def liveness():
    return {"status": "ok"}


@app.get("/api/health/check")
async def manual_check() -> Any:
    issues = []
    for ns in settings.namespaces.split(","):
        issues.extend(_check_namespace(ns.strip()))
    return {"issues": issues, "healthy": len(issues) == 0}
