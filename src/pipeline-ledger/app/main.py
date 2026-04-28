"""FastAPI application entry point for Pipeline Ledger service."""
from __future__ import annotations

import asyncio
import logging

from fastapi import FastAPI
from opentelemetry import trace
from opentelemetry.exporter.otlp.proto.grpc.trace_exporter import OTLPSpanExporter
from opentelemetry.instrumentation.fastapi import FastAPIInstrumentor
from opentelemetry.sdk.resources import Resource
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor

from app.config import settings
from app.projector import run_projector
from app.repository import LedgerRepository
from app.router import router

# ── OTEL setup ──────────────────────────────────────────────────────────────
resource = Resource(attributes={"service.name": settings.otel_service_name})
provider = TracerProvider(resource=resource)
provider.add_span_processor(
    BatchSpanProcessor(OTLPSpanExporter(endpoint=settings.otel_exporter_otlp_endpoint))
)
trace.set_tracer_provider(provider)

logging.basicConfig(level=logging.INFO)

# ── Global repository (injected into router) ───────────────────────────────
_repository: LedgerRepository = LedgerRepository.create()

# ── FastAPI app ─────────────────────────────────────────────────────────────
app = FastAPI(
    title="ORBIT Pipeline Ledger",
    version="1.0.0",
    docs_url="/docs",
    redoc_url=None,
)
app.include_router(router)
FastAPIInstrumentor.instrument_app(app)


@app.on_event("startup")
async def startup():
    await _repository.migrate()
    asyncio.create_task(run_projector(_repository))


@app.get("/health/live")
async def liveness():
    return {"status": "ok"}


@app.get("/health/ready")
async def readiness():
    return {"status": "ok"}
