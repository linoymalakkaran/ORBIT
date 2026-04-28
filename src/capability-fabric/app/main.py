"""Capability Fabric FastAPI application."""
from __future__ import annotations

import logging

from fastapi import FastAPI
from opentelemetry import trace
from opentelemetry.exporter.otlp.proto.grpc.trace_exporter import OTLPSpanExporter
from opentelemetry.instrumentation.fastapi import FastAPIInstrumentor
from opentelemetry.sdk.resources import Resource
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor
from minio import Minio

from app.config import settings
from app.repository import SkillRepository
from app.router import router

# ── OTEL ─────────────────────────────────────────────────────────────────────
resource = Resource(attributes={"service.name": settings.otel_service_name})
provider = TracerProvider(resource=resource)
provider.add_span_processor(
    BatchSpanProcessor(OTLPSpanExporter(endpoint=settings.otel_exporter_otlp_endpoint))
)
trace.set_tracer_provider(provider)

logging.basicConfig(level=logging.INFO)

_repository: SkillRepository = SkillRepository.create()

app = FastAPI(title="ORBIT Capability Fabric", version="1.0.0")
app.include_router(router)
FastAPIInstrumentor.instrument_app(app)


@app.on_event("startup")
async def startup():
    await _repository.migrate()
    # Ensure MinIO bucket exists
    mc = Minio(
        settings.minio_endpoint,
        access_key=settings.minio_access_key,
        secret_key=settings.minio_secret_key,
        secure=False,
    )
    if not mc.bucket_exists(settings.minio_bucket_skills):
        mc.make_bucket(settings.minio_bucket_skills)


@app.get("/health/live")
async def liveness():
    return {"status": "ok"}


@app.get("/health/ready")
async def readiness():
    return {"status": "ok"}
