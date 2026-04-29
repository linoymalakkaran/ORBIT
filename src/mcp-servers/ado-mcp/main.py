"""
Phase 09 – G10: Azure DevOps (ADO) MCP Server
FastAPI service exposing Azure Boards / Repos / Pipelines as MCP tools
callable by ORBIT agents (BA Agent, Ticket Agent, etc.).
"""
import os
from typing import Any, Optional
import httpx
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel

ADO_ORG_URL = os.environ["ADO_ORG_URL"]  # e.g. https://dev.azure.com/adports
ADO_PAT     = os.environ["ADO_PAT"]       # Personal Access Token from Vault

app = FastAPI(title="Azure DevOps MCP", version="1.0.0")


def _headers() -> dict[str, str]:
    import base64
    token = base64.b64encode(f":{ADO_PAT}".encode()).decode()
    return {"Authorization": f"Basic {token}", "Content-Type": "application/json"}


def _wit_url(org_url: str, project: str) -> str:
    return f"{org_url}/{project}/_apis/wit/workitems"


# ── Models ────────────────────────────────────────────────────────────────────

class CreateWorkItemRequest(BaseModel):
    project: str
    type: str  # "Epic" | "Feature" | "User Story" | "Task" | "Bug"
    title: str
    description: str = ""
    parent_id: Optional[int] = None
    story_points: Optional[int] = None
    tags: list[str] = []


class UpdateWorkItemRequest(BaseModel):
    project: str
    work_item_id: int
    fields: dict[str, Any]


class ListWorkItemsRequest(BaseModel):
    project: str
    query: str = "SELECT [Id],[Title],[State] FROM WorkItems WHERE [System.TeamProject] = @project ORDER BY [System.ChangedDate] DESC"


class CreatePullRequestRequest(BaseModel):
    project: str
    repo: str
    source_branch: str
    target_branch: str = "main"
    title: str
    description: str = ""
    work_item_ids: list[int] = []


class TransitionWorkItemRequest(BaseModel):
    project: str
    work_item_id: int
    state: str  # "New" | "Active" | "In Review" | "Closed" | "Resolved"


# ── Health ────────────────────────────────────────────────────────────────────

@app.get("/health/live")
async def live():
    return {"status": "healthy"}


@app.get("/health/ready")
async def ready():
    async with httpx.AsyncClient() as c:
        r = await c.get(f"{ADO_ORG_URL}/_apis/projects?api-version=7.1", headers=_headers(), timeout=5)
        return {"status": "healthy" if r.status_code == 200 else "degraded"}


# ── Tool 1: create_work_item ──────────────────────────────────────────────────

@app.post("/tools/create_work_item")
async def create_work_item(req: CreateWorkItemRequest) -> dict[str, Any]:
    """Creates a work item (Epic, User Story, Task, Bug) in Azure DevOps."""
    work_item_type = req.type.replace(" ", "%20")
    patch_doc = [
        {"op": "add", "path": "/fields/System.Title", "value": req.title},
        {"op": "add", "path": "/fields/System.Description", "value": req.description},
    ]
    if req.story_points:
        patch_doc.append({"op": "add", "path": "/fields/Microsoft.VSTS.Scheduling.StoryPoints", "value": req.story_points})
    if req.tags:
        patch_doc.append({"op": "add", "path": "/fields/System.Tags", "value": "; ".join(req.tags)})
    if req.parent_id:
        patch_doc.append({
            "op": "add",
            "path": "/relations/-",
            "value": {
                "rel": "System.LinkTypes.Hierarchy-Reverse",
                "url": f"{ADO_ORG_URL}/{req.project}/_apis/wit/workitems/{req.parent_id}",
            },
        })

    headers = {**_headers(), "Content-Type": "application/json-patch+json"}
    async with httpx.AsyncClient() as c:
        r = await c.post(
            f"{ADO_ORG_URL}/{req.project}/_apis/wit/workitems/${work_item_type}?api-version=7.1",
            json=patch_doc,
            headers=headers,
            timeout=15,
        )
        if r.status_code not in (200, 201):
            raise HTTPException(r.status_code, r.text[:500])
        item = r.json()
        return {
            "id": item["id"],
            "url": item.get("_links", {}).get("html", {}).get("href", ""),
            "title": req.title,
            "type": req.type,
            "project": req.project,
        }


# ── Tool 2: get_work_item ─────────────────────────────────────────────────────

@app.get("/tools/get_work_item")
async def get_work_item(project: str, work_item_id: int) -> dict[str, Any]:
    """Returns full details of a work item."""
    async with httpx.AsyncClient() as c:
        r = await c.get(
            f"{ADO_ORG_URL}/{project}/_apis/wit/workitems/{work_item_id}?$expand=all&api-version=7.1",
            headers=_headers(),
            timeout=10,
        )
        if r.status_code == 404:
            raise HTTPException(404, f"Work item {work_item_id} not found")
        r.raise_for_status()
        item = r.json()
        fields = item.get("fields", {})
        return {
            "id": item["id"],
            "title": fields.get("System.Title"),
            "state": fields.get("System.State"),
            "type": fields.get("System.WorkItemType"),
            "description": fields.get("System.Description"),
            "story_points": fields.get("Microsoft.VSTS.Scheduling.StoryPoints"),
            "assigned_to": fields.get("System.AssignedTo", {}).get("displayName"),
            "url": item.get("_links", {}).get("html", {}).get("href", ""),
        }


# ── Tool 3: update_work_item ──────────────────────────────────────────────────

@app.patch("/tools/update_work_item")
async def update_work_item(req: UpdateWorkItemRequest) -> dict[str, Any]:
    """Updates fields on an existing work item."""
    patch_doc = [{"op": "replace", "path": f"/fields/{k}", "value": v} for k, v in req.fields.items()]
    headers = {**_headers(), "Content-Type": "application/json-patch+json"}
    async with httpx.AsyncClient() as c:
        r = await c.patch(
            f"{ADO_ORG_URL}/{req.project}/_apis/wit/workitems/{req.work_item_id}?api-version=7.1",
            json=patch_doc,
            headers=headers,
            timeout=10,
        )
        r.raise_for_status()
        return {"success": True, "work_item_id": req.work_item_id}


# ── Tool 4: list_work_items ───────────────────────────────────────────────────

@app.post("/tools/list_work_items")
async def list_work_items(req: ListWorkItemsRequest) -> dict[str, Any]:
    """Executes a WIQL query and returns matching work items."""
    async with httpx.AsyncClient() as c:
        r = await c.post(
            f"{ADO_ORG_URL}/{req.project}/_apis/wit/wiql?api-version=7.1",
            json={"query": req.query},
            headers=_headers(),
            timeout=15,
        )
        r.raise_for_status()
        ids = [wi["id"] for wi in r.json().get("workItems", [])]
        if not ids:
            return {"project": req.project, "items": []}

        # Batch fetch details
        r2 = await c.get(
            f"{ADO_ORG_URL}/_apis/wit/workitems?ids={','.join(map(str, ids[:200]))}&$expand=fields&api-version=7.1",
            headers=_headers(),
            timeout=15,
        )
        r2.raise_for_status()
        items = [
            {
                "id": wi["id"],
                "title": wi["fields"].get("System.Title"),
                "state": wi["fields"].get("System.State"),
                "type": wi["fields"].get("System.WorkItemType"),
            }
            for wi in r2.json().get("value", [])
        ]
        return {"project": req.project, "total": len(items), "items": items}


# ── Tool 5: create_pull_request ───────────────────────────────────────────────

@app.post("/tools/create_pull_request")
async def create_pull_request(req: CreatePullRequestRequest) -> dict[str, Any]:
    """Creates a pull request in Azure DevOps Repos."""
    payload: dict[str, Any] = {
        "title": req.title,
        "description": req.description,
        "sourceRefName": f"refs/heads/{req.source_branch}",
        "targetRefName": f"refs/heads/{req.target_branch}",
    }
    if req.work_item_ids:
        payload["workItemRefs"] = [{"id": str(wid)} for wid in req.work_item_ids]

    async with httpx.AsyncClient() as c:
        r = await c.post(
            f"{ADO_ORG_URL}/{req.project}/_apis/git/repositories/{req.repo}/pullrequests?api-version=7.1",
            json=payload,
            headers=_headers(),
            timeout=15,
        )
        if r.status_code not in (200, 201):
            raise HTTPException(r.status_code, r.text[:500])
        pr = r.json()
        return {
            "pr_id": pr["pullRequestId"],
            "url": pr.get("url", ""),
            "title": req.title,
            "source_branch": req.source_branch,
            "target_branch": req.target_branch,
            "status": pr.get("status", "active"),
        }


# ── Tool 6: transition_work_item ──────────────────────────────────────────────

@app.post("/tools/transition_work_item")
async def transition_work_item(req: TransitionWorkItemRequest) -> dict[str, Any]:
    """Transitions a work item to a new state (e.g. 'In Review', 'Closed')."""
    patch_doc = [{"op": "replace", "path": "/fields/System.State", "value": req.state}]
    headers = {**_headers(), "Content-Type": "application/json-patch+json"}
    async with httpx.AsyncClient() as c:
        r = await c.patch(
            f"{ADO_ORG_URL}/{req.project}/_apis/wit/workitems/{req.work_item_id}?api-version=7.1",
            json=patch_doc,
            headers=headers,
            timeout=10,
        )
        if r.status_code == 400:
            raise HTTPException(400, f"Invalid transition to '{req.state}': {r.text[:300]}")
        r.raise_for_status()
        return {"success": True, "work_item_id": req.work_item_id, "new_state": req.state}
