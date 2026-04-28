"""PM Agent — sprint planning, task breakdown, status reporting."""
from __future__ import annotations

import json
import logging
from fastapi import FastAPI
from opentelemetry.instrumentation.fastapi import FastAPIInstrumentor
from pydantic import BaseModel
from pydantic_settings import BaseSettings, SettingsConfigDict
import httpx
import litellm

logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO)


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_prefix="PM_", env_file=".env", extra="ignore")
    litellm_api_base: str = "http://litellm-gateway.ai-portal.svc:4000"
    litellm_api_key: str = "changeme"
    default_model: str = "gpt-4o-mini"
    jira_mcp_url: str = "http://jira-mcp.ai-portal.svc:8000"


settings = Settings()
litellm.api_base = settings.litellm_api_base
litellm.api_key  = settings.litellm_api_key

app = FastAPI(title="ORBIT PM Agent", version="1.0.0")
FastAPIInstrumentor.instrument_app(app)


class SprintPlanRequest(BaseModel):
    user_stories: list[str]
    sprint_capacity_points: int = 40
    team_size: int = 5


class StatusReportRequest(BaseModel):
    project_id: str
    sprint_id: str = ""


@app.post("/api/sprint-plan")
async def plan_sprint(req: SprintPlanRequest):
    stories_text = "\n".join(f"- {s}" for s in req.user_stories)
    prompt = f"""As a PM, create a sprint plan from these user stories.
Team capacity: {req.sprint_capacity_points} story points, {req.team_size} members.
Output a prioritised sprint backlog with point estimates. Output as JSON array.

Stories:
{stories_text}"""
    response = await litellm.acompletion(
        model=settings.default_model,
        messages=[{"role": "user", "content": prompt}],
        temperature=0.1,
        response_format={"type": "json_object"},
    )
    return json.loads(response.choices[0].message.content or "[]")


@app.post("/api/status-report")
async def status_report(req: StatusReportRequest):
    prompt = f"""Generate a concise weekly status report for project {req.project_id}.
Include: completed work, in-progress items, blockers, risks, next week plan.
Format as markdown."""
    response = await litellm.acompletion(
        model=settings.default_model,
        messages=[{"role": "user", "content": prompt}],
        temperature=0.2,
    )
    return {"report": response.choices[0].message.content}


@app.get("/health/live")
async def liveness():
    return {"status": "ok"}
