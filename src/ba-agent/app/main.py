"""BA Agent — requirements extraction, user story generation, estimation."""
from __future__ import annotations

import json
import logging
import uuid
from typing import Any, Optional
import httpx
from fastapi import FastAPI, HTTPException
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
    jira_mcp_url: str = "http://jira-mcp.ai-portal.svc:80"
    ado_mcp_url: str = "http://ado-mcp.ai-portal.svc:80"
    ledger_url: str = "http://pipeline-ledger.ai-portal.svc:80"


settings = Settings()
litellm.api_base = settings.litellm_api_base
litellm.api_key  = settings.litellm_api_key

app = FastAPI(title="ORBIT BA Agent", version="1.0.0")
FastAPIInstrumentor.instrument_app(app)

# ── In-memory story review store (keyed by review_id) ───────────────────────
_reviews: dict[str, dict[str, Any]] = {}


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
    return json.loads(response.choices[0].message.content or "{}")


# ── G19: Story Review Gate ────────────────────────────────────────────────────

class StoryReviewRequest(BaseModel):
    project_id: str
    stories: list[dict[str, Any]]   # list of story objects from /api/analyse


class SyncToJiraRequest(BaseModel):
    review_id: str
    jira_project_key: str
    epic_name: Optional[str] = None
    jira_mcp_url: Optional[str] = None


class SyncToAdoRequest(BaseModel):
    review_id: str
    ado_project: str
    ado_org: Optional[str] = None
    ado_mcp_url: Optional[str] = None


@app.post("/api/review")
async def submit_for_review(req: StoryReviewRequest) -> dict[str, Any]:
    """
    Phase 22 – G19 (step 1): Stores generated stories in pending_review state.
    Returns a review_id. Sync is blocked until PATCH /api/review/{id}/approve.
    """
    review_id = str(uuid.uuid4())
    _reviews[review_id] = {
        "review_id": review_id,
        "project_id": req.project_id,
        "stories": req.stories,
        "status": "pending_review",
        "review_url": f"/api/review/{review_id}",
    }
    logger.info("Stories submitted for review: review_id=%s, story_count=%d", review_id, len(req.stories))
    return {
        "review_id": review_id,
        "status": "pending_review",
        "story_count": len(req.stories),
        "review_url": f"/api/review/{review_id}",
        "message": "Stories are pending human review. Call PATCH /api/review/{review_id}/approve to approve.",
    }


@app.get("/api/review/{review_id}")
async def get_review(review_id: str) -> dict[str, Any]:
    """Returns the current state of a story review."""
    if review_id not in _reviews:
        raise HTTPException(404, f"Review '{review_id}' not found")
    return _reviews[review_id]


@app.patch("/api/review/{review_id}/approve")
async def approve_review(review_id: str) -> dict[str, Any]:
    """Human approves the story review, unblocking sync to Jira/ADO."""
    if review_id not in _reviews:
        raise HTTPException(404, f"Review '{review_id}' not found")
    if _reviews[review_id]["status"] != "pending_review":
        raise HTTPException(409, f"Review already in state: {_reviews[review_id]['status']}")
    _reviews[review_id]["status"] = "approved"
    return {"review_id": review_id, "status": "approved"}


@app.post("/api/sync-to-jira")
async def sync_to_jira(req: SyncToJiraRequest) -> dict[str, Any]:
    """
    Phase 22 – G19 (step 2): Syncs approved stories to Jira.
    Creates Epic first, then User Stories as children.
    """
    if req.review_id not in _reviews:
        raise HTTPException(404, f"Review '{req.review_id}' not found")
    review = _reviews[req.review_id]
    if review["status"] != "approved":
        raise HTTPException(403, "Stories must be approved before syncing. Call PATCH /api/review/{id}/approve first.")

    jira_url = req.jira_mcp_url or settings.jira_mcp_url
    stories = review["stories"]
    created: list[dict] = []

    async with httpx.AsyncClient(timeout=30) as c:
        # 1. Create Epic
        epic_title = req.epic_name or f"Epic — {review['project_id']}"
        r = await c.post(f"{jira_url}/tools/create_issue", json={
            "project_key": req.jira_project_key,
            "issue_type": "Epic",
            "summary": epic_title,
            "description": f"Auto-generated epic for project {review['project_id']} by ORBIT BA Agent",
        })
        if r.status_code not in (200, 201):
            raise HTTPException(502, f"Jira MCP returned {r.status_code} creating Epic")
        epic = r.json()
        epic_key = epic.get("key") or epic.get("id", "UNKNOWN")

        # 2. Create each story under the epic
        for story in stories:
            story_summary = story.get("title") or story.get("summary") or str(story)[:100]
            story_body = {
                "project_key": req.jira_project_key,
                "issue_type": "Story",
                "summary": story_summary,
                "description": story.get("acceptance_criteria") or story.get("description") or "",
                "parent_key": epic_key,
                "story_points": story.get("story_points"),
            }
            rs = await c.post(f"{jira_url}/tools/create_issue", json=story_body)
            if rs.status_code in (200, 201):
                created.append({"jira_key": rs.json().get("key"), "title": story_summary})
            else:
                logger.warning("Failed to create Jira story '%s': %s", story_summary, rs.text[:200])

    _reviews[req.review_id]["status"] = "synced_jira"

    # Record in ledger
    try:
        async with httpx.AsyncClient(timeout=5) as c:
            await c.post(f"{settings.ledger_url}/api/ledger", json={
                "project_id": review["project_id"],
                "event_type": "stories.synced_to_jira",
                "payload": {"epic_key": epic_key, "story_count": len(created)},
            })
    except Exception:
        pass

    return {
        "review_id": req.review_id,
        "jira_project_key": req.jira_project_key,
        "epic_key": epic_key,
        "stories_created": len(created),
        "stories": created,
    }


@app.post("/api/sync-to-ado")
async def sync_to_ado(req: SyncToAdoRequest) -> dict[str, Any]:
    """
    Phase 22 – G19 (step 2 alt): Syncs approved stories to Azure DevOps.
    Creates Epic first, then User Stories as children.
    """
    if req.review_id not in _reviews:
        raise HTTPException(404, f"Review '{req.review_id}' not found")
    review = _reviews[req.review_id]
    if review["status"] != "approved":
        raise HTTPException(403, "Stories must be approved before syncing. Call PATCH /api/review/{id}/approve first.")

    ado_url = req.ado_mcp_url or settings.ado_mcp_url
    stories = review["stories"]
    created: list[dict] = []

    async with httpx.AsyncClient(timeout=30) as c:
        # 1. Create Epic
        r = await c.post(f"{ado_url}/tools/create_work_item", json={
            "project": req.ado_project,
            "type": "Epic",
            "title": f"Epic — {review['project_id']}",
            "description": f"Auto-generated epic for project {review['project_id']} by ORBIT BA Agent",
        })
        if r.status_code not in (200, 201):
            raise HTTPException(502, f"ADO MCP returned {r.status_code} creating Epic")
        epic_id = r.json().get("id")

        # 2. Create each story under the epic
        for story in stories:
            story_title = story.get("title") or story.get("summary") or str(story)[:100]
            rs = await c.post(f"{ado_url}/tools/create_work_item", json={
                "project": req.ado_project,
                "type": "User Story",
                "title": story_title,
                "description": story.get("acceptance_criteria") or story.get("description") or "",
                "parent_id": epic_id,
                "story_points": story.get("story_points"),
            })
            if rs.status_code in (200, 201):
                created.append({"ado_id": rs.json().get("id"), "title": story_title})
            else:
                logger.warning("Failed to create ADO story '%s': %s", story_title, rs.text[:200])

    _reviews[req.review_id]["status"] = "synced_ado"

    # Record in ledger
    try:
        async with httpx.AsyncClient(timeout=5) as c:
            await c.post(f"{settings.ledger_url}/api/ledger", json={
                "project_id": review["project_id"],
                "event_type": "stories.synced_to_ado",
                "payload": {"epic_id": epic_id, "story_count": len(created)},
            })
    except Exception:
        pass

    return {
        "review_id": req.review_id,
        "ado_project": req.ado_project,
        "epic_id": epic_id,
        "stories_created": len(created),
        "stories": created,
    }


@app.get("/health/live")
async def liveness():
    return {"status": "ok"}


@app.get("/health/ready")
async def readiness():
    return {"status": "ok"}
