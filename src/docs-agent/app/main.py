"""Documentation Agent — generates README, ADR, runbooks, API references."""
from __future__ import annotations

import logging
from fastapi import FastAPI
from opentelemetry.instrumentation.fastapi import FastAPIInstrumentor
from pydantic import BaseModel
from pydantic_settings import BaseSettings, SettingsConfigDict
import litellm

logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO)


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_prefix="DOCS_", env_file=".env", extra="ignore")
    litellm_api_base: str = "http://litellm-gateway.ai-portal.svc:4000"
    litellm_api_key: str = "changeme"
    default_model: str = "gpt-4o-mini"
    confluence_mcp_url: str = "http://confluence-mcp.ai-portal.svc:8000"


settings = Settings()
litellm.api_base = settings.litellm_api_base
litellm.api_key  = settings.litellm_api_key

app = FastAPI(title="ORBIT Documentation Agent", version="1.0.0")
FastAPIInstrumentor.instrument_app(app)


class DocRequest(BaseModel):
    doc_type: str  # readme | adr | runbook | api_ref
    context: str
    service_name: str = ""


DOC_PROMPTS = {
    "readme": "Generate a comprehensive README.md for a microservice. Include: overview, architecture, setup, configuration, API reference, deployment.",
    "adr": "Generate an Architecture Decision Record (ADR) in Markdown format following the Michael Nygard template.",
    "runbook": "Generate an operational runbook in Markdown format with: overview, prerequisites, procedures, troubleshooting, escalation.",
    "api_ref": "Generate OpenAPI 3.1 YAML documentation from the provided API description.",
}


@app.post("/api/generate")
async def generate_doc(req: DocRequest):
    system_prompt = DOC_PROMPTS.get(req.doc_type, DOC_PROMPTS["readme"])
    response = await litellm.acompletion(
        model=settings.default_model,
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": f"Service: {req.service_name}\n\n{req.context}"},
        ],
        temperature=0.2,
    )
    return {
        "doc_type": req.doc_type,
        "service_name": req.service_name,
        "content": response.choices[0].message.content,
    }


@app.get("/health/live")
async def liveness():
    return {"status": "ok"}


@app.get("/health/ready")
async def readiness():
    return {"status": "ok"}
