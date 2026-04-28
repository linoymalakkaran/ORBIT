"""PR Review Agent — LangGraph-powered autonomous MR reviewer for GitLab."""
from __future__ import annotations

import asyncio
import json
import logging
from typing import Annotated, TypedDict
import operator

import httpx
from fastapi import FastAPI, Depends
from opentelemetry.instrumentation.fastapi import FastAPIInstrumentor
from langgraph.graph import StateGraph, END
from pydantic import BaseModel
from pydantic_settings import BaseSettings, SettingsConfigDict

logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO)


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_prefix="PRREVIEW_", env_file=".env", extra="ignore")
    gitlab_url: str = "https://gitlab.adports.ae"
    gitlab_token: str = ""
    litellm_api_base: str = "http://litellm-gateway.ai-portal.svc:4000"
    litellm_api_key: str = "changeme"
    default_model: str = "gpt-4o-mini"
    keycloak_issuer: str = "https://auth.ai.adports.ae/realms/ai-portal"
    keycloak_audience: str = "portal-api"


settings = Settings()

import litellm
litellm.api_base = settings.litellm_api_base
litellm.api_key  = settings.litellm_api_key


class ReviewState(TypedDict):
    project_path: str
    mr_iid: int
    diff: str
    review_comments: Annotated[list[str], operator.add]
    risk_score: int
    approved: bool


async def _fetch_diff(state: ReviewState) -> dict:
    encoded = state["project_path"].replace("/", "%2F")
    url = f"{settings.gitlab_url}/api/v4/projects/{encoded}/merge_requests/{state['mr_iid']}/diffs"
    async with httpx.AsyncClient() as client:
        r = await client.get(url, headers={"PRIVATE-TOKEN": settings.gitlab_token})
        r.raise_for_status()
    diffs = r.json()
    diff_text = "\n".join(d.get("diff", "") for d in diffs[:10])  # limit for LLM context
    return {"diff": diff_text[:8000]}


async def _analyse_diff(state: ReviewState) -> dict:
    response = await litellm.acompletion(
        model=settings.default_model,
        messages=[
            {"role": "system", "content": "You are an expert code reviewer. Analyse this diff for bugs, security issues, and code quality. Rate risk 1-10."},
            {"role": "user", "content": state["diff"]},
        ],
        temperature=0.1,
    )
    content = response.choices[0].message.content or ""
    risk = 5
    for line in content.lower().split("\n"):
        if "risk" in line and any(c.isdigit() for c in line):
            digits = [int(c) for c in line if c.isdigit()]
            if digits:
                risk = min(10, max(1, digits[0]))
                break
    return {"review_comments": [content], "risk_score": risk}


async def _post_comments(state: ReviewState) -> dict:
    encoded = state["project_path"].replace("/", "%2F")
    url = f"{settings.gitlab_url}/api/v4/projects/{encoded}/merge_requests/{state['mr_iid']}/notes"
    body = f"**ORBIT AI Review** (Risk Score: {state['risk_score']}/10)\n\n{state['review_comments'][-1]}"
    async with httpx.AsyncClient() as client:
        await client.post(url, headers={"PRIVATE-TOKEN": settings.gitlab_token}, json={"body": body})
    approved = state["risk_score"] <= 6
    return {"approved": approved}


def _build_graph():
    g = StateGraph(ReviewState)
    g.add_node("fetch_diff", _fetch_diff)
    g.add_node("analyse_diff", _analyse_diff)
    g.add_node("post_comments", _post_comments)
    g.add_edge("fetch_diff", "analyse_diff")
    g.add_edge("analyse_diff", "post_comments")
    g.add_edge("post_comments", END)
    g.set_entry_point("fetch_diff")
    return g.compile()


_graph = _build_graph()

app = FastAPI(title="ORBIT PR Review Agent", version="1.0.0")
FastAPIInstrumentor.instrument_app(app)


class ReviewRequest(BaseModel):
    project_path: str
    mr_iid: int


@app.post("/api/review")
async def review_mr(req: ReviewRequest):
    state = ReviewState(
        project_path=req.project_path,
        mr_iid=req.mr_iid,
        diff="", review_comments=[], risk_score=5, approved=False
    )
    result = await _graph.ainvoke(state)
    return {"risk_score": result["risk_score"], "approved": result["approved"]}


@app.get("/health/live")
async def liveness():
    return {"status": "ok"}
