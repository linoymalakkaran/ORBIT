"""Hook Engine — receives GitLab webhooks and triggers ORBIT pipeline."""
from __future__ import annotations

import hashlib
import hmac
import json
import logging
import os
from typing import Any

import httpx
from confluent_kafka import Producer
from fastapi import FastAPI, HTTPException, Request, status
from opentelemetry import trace
from opentelemetry.exporter.otlp.proto.grpc.trace_exporter import OTLPSpanExporter
from opentelemetry.instrumentation.fastapi import FastAPIInstrumentor
from opentelemetry.sdk.resources import Resource
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor
from pydantic import BaseModel
from pydantic_settings import BaseSettings, SettingsConfigDict

logger = logging.getLogger(__name__)


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_prefix="HOOK_", env_file=".env", extra="ignore")
    webhook_secret: str = "changeme"
    kafka_bootstrap_servers: str = "kafka:9092"
    kafka_topic: str = "orbit.pipeline.events"
    orchestrator_url: str = "http://orchestrator.ai-portal.svc:80"
    orbit_service_token: str = ""
    otel_exporter_otlp_endpoint: str = "http://otel-collector:4317"
    otel_service_name: str = "hook-engine"


settings = Settings()

# OTEL
resource = Resource(attributes={"service.name": settings.otel_service_name})
provider = TracerProvider(resource=resource)
provider.add_span_processor(
    BatchSpanProcessor(OTLPSpanExporter(endpoint=settings.otel_exporter_otlp_endpoint))
)
trace.set_tracer_provider(provider)

_producer = Producer({"bootstrap.servers": settings.kafka_bootstrap_servers})

app = FastAPI(title="ORBIT Hook Engine", version="1.0.0")
FastAPIInstrumentor.instrument_app(app)


def _verify_gitlab_signature(body: bytes, signature: str) -> bool:
    expected = hmac.new(settings.webhook_secret.encode(), body, hashlib.sha256).hexdigest()
    return hmac.compare_digest(f"sha256={expected}", signature)


@app.post("/webhooks/gitlab")
async def gitlab_webhook(request: Request) -> Any:
    body = await request.body()
    sig = request.headers.get("X-Gitlab-Token", "")
    # GitLab sends a simple token, not HMAC — compare directly
    if not hmac.compare_digest(sig.encode(), settings.webhook_secret.encode()):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Invalid webhook token")

    payload = json.loads(body)
    event = request.headers.get("X-Gitlab-Event", "")
    logger.info("Received GitLab event: %s", event)

    # Publish to Kafka for downstream consumers
    _producer.produce(
        settings.kafka_topic,
        key=event.encode(),
        value=json.dumps({"event": event, "payload": payload}).encode(),
    )
    _producer.poll(0)

    # Trigger pipeline on MR merge events
    if event == "Merge Request Hook" and payload.get("object_attributes", {}).get("action") == "merge":
        mr = payload["object_attributes"]
        project = payload.get("project", {})
        await _trigger_pipeline(
            project_name=project.get("name", "unknown"),
            requirements=f"MR merged: {mr.get('title')}\n{mr.get('description', '')}",
        )

    return {"received": True, "event": event}


async def _trigger_pipeline(project_name: str, requirements: str):
    headers = {"Authorization": f"Bearer {settings.orbit_service_token}"}
    async with httpx.AsyncClient(timeout=10) as client:
        await client.post(
            f"{settings.orchestrator_url}/api/pipelines",
            json={"project_name": project_name, "requirements": requirements,
                  "project_id": "00000000-0000-0000-0000-000000000000"},
            headers=headers,
        )


@app.get("/health/live")
async def liveness():
    return {"status": "ok"}
