"""Harbor MCP Server — container image and vulnerability report tools."""
from __future__ import annotations

import os
import sys
import httpx
import uvicorn

sys.path.insert(0, str(__import__("pathlib").Path(__file__).parent.parent))
from shared.mcp_base import McpServer

HARBOR_URL      = os.environ.get("HARBOR_URL", "https://harbor.ai.adports.ae")
HARBOR_USER     = os.environ.get("HARBOR_USER", "robot$orbit-agent")
HARBOR_PASSWORD = os.environ.get("HARBOR_PASSWORD", "")

server = McpServer(title="Harbor MCP", version="1.0.0")


def _auth() -> tuple:
    return (HARBOR_USER, HARBOR_PASSWORD)


@server.tool(
    name="list_repositories",
    description="List repositories in a Harbor project",
    input_schema={
        "type": "object",
        "required": ["project_name"],
        "properties": {
            "project_name": {"type": "string", "description": "e.g. 'orbit'"},
            "page_size": {"type": "integer", "default": 20},
        }
    }
)
async def list_repositories(project_name: str, page_size: int = 20):
    url = f"{HARBOR_URL}/api/v2.0/projects/{project_name}/repositories"
    async with httpx.AsyncClient() as client:
        r = await client.get(url, auth=_auth(), params={"page_size": page_size})
        r.raise_for_status()
    return r.json()


@server.tool(
    name="get_vulnerability_report",
    description="Get Trivy vulnerability report for a specific image tag",
    input_schema={
        "type": "object",
        "required": ["project_name", "repository_name", "tag"],
        "properties": {
            "project_name": {"type": "string"},
            "repository_name": {"type": "string"},
            "tag": {"type": "string"},
        }
    }
)
async def get_vulnerability_report(project_name: str, repository_name: str, tag: str):
    repo_encoded = repository_name.replace("/", "%2F")
    url = (f"{HARBOR_URL}/api/v2.0/projects/{project_name}/repositories/"
           f"{repo_encoded}/artifacts/{tag}/additions/vulnerabilities")
    async with httpx.AsyncClient() as client:
        r = await client.get(url, auth=_auth())
        r.raise_for_status()
    return r.json()


@server.tool(
    name="list_artifacts",
    description="List artifacts (images) in a Harbor repository",
    input_schema={
        "type": "object",
        "required": ["project_name", "repository_name"],
        "properties": {
            "project_name": {"type": "string"},
            "repository_name": {"type": "string"},
            "page_size": {"type": "integer", "default": 20},
        }
    }
)
async def list_artifacts(project_name: str, repository_name: str, page_size: int = 20):
    repo_encoded = repository_name.replace("/", "%2F")
    url = f"{HARBOR_URL}/api/v2.0/projects/{project_name}/repositories/{repo_encoded}/artifacts"
    async with httpx.AsyncClient() as client:
        r = await client.get(url, auth=_auth(), params={"page_size": page_size, "with_scan_overview": True})
        r.raise_for_status()
    return r.json()


app = server.app
if __name__ == "__main__":
    uvicorn.run("main:app", host="0.0.0.0", port=8000)
