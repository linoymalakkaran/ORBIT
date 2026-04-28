"""GitLab MCP Server — repository, MR and pipeline tools."""
from __future__ import annotations

import os
import sys
import httpx
import uvicorn

sys.path.insert(0, str(__import__("pathlib").Path(__file__).parent.parent))
from shared.mcp_base import McpServer

GITLAB_URL   = os.environ.get("GITLAB_URL", "https://gitlab.adports.ae")
GITLAB_TOKEN = os.environ.get("GITLAB_TOKEN", "")

_headers = {"PRIVATE-TOKEN": GITLAB_TOKEN, "Content-Type": "application/json"}

server = McpServer(title="GitLab MCP", version="1.0.0")


@server.tool(
    name="list_merge_requests",
    description="List open merge requests for a GitLab project",
    input_schema={
        "type": "object",
        "required": ["project_path"],
        "properties": {
            "project_path": {"type": "string", "description": "e.g. 'group/repo'"},
            "state": {"type": "string", "default": "opened"},
        }
    }
)
async def list_merge_requests(project_path: str, state: str = "opened"):
    encoded = project_path.replace("/", "%2F")
    url = f"{GITLAB_URL}/api/v4/projects/{encoded}/merge_requests"
    async with httpx.AsyncClient() as client:
        r = await client.get(url, headers=_headers, params={"state": state, "per_page": 20})
        r.raise_for_status()
    return r.json()


@server.tool(
    name="get_mr_diff",
    description="Get the diff for a specific merge request",
    input_schema={
        "type": "object",
        "required": ["project_path", "mr_iid"],
        "properties": {
            "project_path": {"type": "string"},
            "mr_iid": {"type": "integer"},
        }
    }
)
async def get_mr_diff(project_path: str, mr_iid: int):
    encoded = project_path.replace("/", "%2F")
    url = f"{GITLAB_URL}/api/v4/projects/{encoded}/merge_requests/{mr_iid}/diffs"
    async with httpx.AsyncClient() as client:
        r = await client.get(url, headers=_headers)
        r.raise_for_status()
    return r.json()


@server.tool(
    name="post_mr_comment",
    description="Post a review comment on a merge request",
    input_schema={
        "type": "object",
        "required": ["project_path", "mr_iid", "body"],
        "properties": {
            "project_path": {"type": "string"},
            "mr_iid": {"type": "integer"},
            "body": {"type": "string"},
        }
    }
)
async def post_mr_comment(project_path: str, mr_iid: int, body: str):
    encoded = project_path.replace("/", "%2F")
    url = f"{GITLAB_URL}/api/v4/projects/{encoded}/merge_requests/{mr_iid}/notes"
    async with httpx.AsyncClient() as client:
        r = await client.post(url, headers=_headers, json={"body": body})
        r.raise_for_status()
    return r.json()


@server.tool(
    name="trigger_pipeline",
    description="Trigger a CI pipeline for a branch",
    input_schema={
        "type": "object",
        "required": ["project_path", "ref"],
        "properties": {
            "project_path": {"type": "string"},
            "ref": {"type": "string", "description": "Branch or tag name"},
            "variables": {"type": "object", "description": "Pipeline variables", "default": {}},
        }
    }
)
async def trigger_pipeline(project_path: str, ref: str, variables: dict = {}):
    encoded = project_path.replace("/", "%2F")
    url = f"{GITLAB_URL}/api/v4/projects/{encoded}/pipeline"
    vars_list = [{"key": k, "value": v} for k, v in variables.items()]
    async with httpx.AsyncClient() as client:
        r = await client.post(url, headers=_headers, json={"ref": ref, "variables": vars_list})
        r.raise_for_status()
    return r.json()


@server.tool(
    name="get_file_content",
    description="Retrieve a file from a GitLab repository",
    input_schema={
        "type": "object",
        "required": ["project_path", "file_path"],
        "properties": {
            "project_path": {"type": "string"},
            "file_path": {"type": "string"},
            "ref": {"type": "string", "default": "main"},
        }
    }
)
async def get_file_content(project_path: str, file_path: str, ref: str = "main"):
    import base64
    encoded_proj = project_path.replace("/", "%2F")
    encoded_file = file_path.replace("/", "%2F")
    url = f"{GITLAB_URL}/api/v4/projects/{encoded_proj}/repository/files/{encoded_file}"
    async with httpx.AsyncClient() as client:
        r = await client.get(url, headers=_headers, params={"ref": ref})
        r.raise_for_status()
    data = r.json()
    content = base64.b64decode(data.get("content", "")).decode("utf-8", errors="replace")
    return {"file_path": file_path, "ref": ref, "content": content}


app = server.app

if __name__ == "__main__":
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=False)
