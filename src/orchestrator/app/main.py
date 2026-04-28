"""Orchestrator FastAPI application + Temporal worker startup."""
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
from app.router import router
from app.temporal_worker import start_worker

resource = Resource(attributes={"service.name": settings.otel_service_name})
provider = TracerProvider(resource=resource)
provider.add_span_processor(
    BatchSpanProcessor(OTLPSpanExporter(endpoint=settings.otel_exporter_otlp_endpoint))
)
trace.set_tracer_provider(provider)

logging.basicConfig(level=logging.INFO)

app = FastAPI(title="ORBIT Orchestrator", version="1.0.0")
app.include_router(router)
FastAPIInstrumentor.instrument_app(app)


@app.on_event("startup")
async def startup():
    # Start Temporal worker in background
    asyncio.create_task(start_worker())


@app.get("/health/live")
async def liveness():
    return {"status": "ok"}


@app.get("/health/ready")
async def readiness():
    return {"status": "ok"}
