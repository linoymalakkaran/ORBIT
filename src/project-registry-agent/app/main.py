"""Project Registry Agent — syncs GitLab projects into ORBIT portal."""
from __future__ import annotations

import asyncio
import json
import logging
import os
from typing import Any

import httpx
from confluent_kafka import Consumer, KafkaError
from fastapi import FastAPI
from opentelemetry import trace
from opentelemetry.exporter.otlp.proto.grpc.trace_exporter import OTLPSpanExporter
from opentelemetry.instrumentation.fastapi import FastAPIInstrumentor
from opentelemetry.sdk.resources import Resource
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor
from pydantic_settings import BaseSettings, SettingsConfigDict

logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO)


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_prefix="REGISTRY_", env_file=".env", extra="ignore")
    gitlab_url: str = "https://gitlab.adports.ae"
    gitlab_token: str = ""
    portal_api_url: str = "http://portal-api.ai-portal.svc:80"
    portal_service_token: str = ""
    kafka_bootstrap_servers: str = "kafka:9092"
    kafka_topic: str = "orbit.pipeline.events"
    kafka_group: str = "project-registry-agent"
    otel_exporter_otlp_endpoint: str = "http://otel-collector:4317"
    otel_service_name: str = "project-registry-agent"


settings = Settings()

resource = Resource(attributes={"service.name": settings.otel_service_name})
provider = TracerProvider(resource=resource)
provider.add_span_processor(
    BatchSpanProcessor(OTLPSpanExporter(endpoint=settings.otel_exporter_otlp_endpoint))
)
trace.set_tracer_provider(provider)

app = FastAPI(title="ORBIT Project Registry Agent", version="1.0.0")
FastAPIInstrumentor.instrument_app(app)


async def _sync_gitlab_project(project_path: str) -> None:
    headers = {"PRIVATE-TOKEN": settings.gitlab_token}
    encoded = project_path.replace("/", "%2F")
    async with httpx.AsyncClient() as client:
        r = await client.get(f"{settings.gitlab_url}/api/v4/projects/{encoded}", headers=headers)
        if r.status_code != 200:
            logger.warning("GitLab project not found: %s", project_path)
            return
        gl_data = r.json()

    portal_payload = {
        "displayName": gl_data.get("name", project_path),
        "slug": gl_data.get("path_with_namespace", project_path).replace("/", "-"),
        "description": gl_data.get("description", ""),
        "program": None,
    }
    portal_headers = {"Authorization": f"Bearer {settings.portal_service_token}"}
    async with httpx.AsyncClient() as client:
        r = await client.post(
            f"{settings.portal_api_url}/api/projects",
            json=portal_payload, headers=portal_headers
        )
    logger.info("Synced project %s → portal (status %d)", project_path, r.status_code)


async def _kafka_consumer_loop() -> None:
    consumer = Consumer({
        "bootstrap.servers": settings.kafka_bootstrap_servers,
        "group.id": settings.kafka_group,
        "auto.offset.reset": "earliest",
        "enable.auto.commit": True,
    })
    consumer.subscribe([settings.kafka_topic])
    try:
        while True:
            msg = consumer.poll(1.0)
            if msg is None:
                await asyncio.sleep(0.01)
                continue
            if msg.error():
                if msg.error().code() != KafkaError._PARTITION_EOF:
                    logger.error("Kafka error: %s", msg.error())
                continue
            data = json.loads(msg.value())
            if data.get("event") == "Push Hook":
                project_path = data.get("payload", {}).get("project", {}).get("path_with_namespace")
                if project_path:
                    await _sync_gitlab_project(project_path)
    finally:
        consumer.close()


@app.on_event("startup")
async def startup():
    asyncio.create_task(_kafka_consumer_loop())


@app.get("/health/live")
async def liveness():
    return {"status": "ok"}


@app.post("/api/sync/{project_path:path}")
async def manual_sync(project_path: str) -> Any:
    await _sync_gitlab_project(project_path)
    return {"synced": project_path}
