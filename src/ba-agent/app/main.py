"""BA Agent — requirements extraction, user story generation, estimation."""
from __future__ import annotations

import logging
from fastapi import FastAPI, Depends
from opentelemetry.instrumentation.fastapi import FastAPIInstrumentor
from pydantic import BaseModel
from pydantic_settings import BaseSettings, SettingsConfigDict
import litellm

logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO)


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_prefix="BA_", env_file=".env", extra="ignore")
    litellm_api_base: str = "http://litellm-gateway.ai-portal.svc:4000"
    litellm_api_key: str = "changeme"
    default_model: str = "gpt-4o-mini"


settings = Settings()
litellm.api_base = settings.litellm_api_base
litellm.api_key  = settings.litellm_api_key

app = FastAPI(title="ORBIT BA Agent", version="1.0.0")
FastAPIInstrumentor.instrument_app(app)


class AnalyseRequest(BaseModel):
    raw_requirements: str
    project_context: str = ""


@app.post("/api/analyse")
async def analyse(req: AnalyseRequest):
    prompt = f"""You are a senior business analyst.
Project context: {req.project_context}

Extract from the following requirements:
1. User stories (As a <role>, I want <feature>, so that <benefit>)
2. Acceptance criteria for each story
3. Edge cases and constraints
4. Non-functional requirements

Requirements:
{req.raw_requirements}"""

    response = await litellm.acompletion(
        model=settings.default_model,
        messages=[{"role": "user", "content": prompt}],
        temperature=0.1,
    )
    return {"analysis": response.choices[0].message.content}


@app.post("/api/estimate")
async def estimate(req: AnalyseRequest):
    prompt = f"""Using three-point estimation (optimistic/most-likely/pessimistic), estimate effort in story points for:
{req.raw_requirements}
Output as JSON with keys: optimistic, most_likely, pessimistic, expected (PERT formula)."""

    response = await litellm.acompletion(
        model=settings.default_model,
        messages=[{"role": "user", "content": prompt}],
        temperature=0.1,
        response_format={"type": "json_object"},
    )
    import json
    return json.loads(response.choices[0].message.content or "{}")


@app.get("/health/live")
async def liveness():
    return {"status": "ok"}
