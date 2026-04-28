"""MCP Registry — central catalogue of all MCP server endpoints."""
from __future__ import annotations

import os
import httpx
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from typing import Optional

app = FastAPI(title="ORBIT MCP Registry", version="1.0.0")

# Registry is populated from environment or config; in production seeded from ConfigMap.
_REGISTRY: dict[str, dict] = {
    "keycloak-mcp": {
        "id": "keycloak-mcp",
        "display_name": "Keycloak MCP",
        "url": os.environ.get("MCP_KEYCLOAK_URL", "http://keycloak-mcp.ai-portal.svc:8000"),
        "description": "Identity and access management operations via Keycloak API",
        "capabilities": ["realm_management", "user_management", "token_introspection"],
    },
    "gitlab-mcp": {
        "id": "gitlab-mcp",
        "display_name": "GitLab MCP",
        "url": os.environ.get("MCP_GITLAB_URL", "http://gitlab-mcp.ai-portal.svc:8000"),
        "description": "Git repository, MR, pipeline and CI/CD operations via GitLab API",
        "capabilities": ["repo_read", "mr_review", "pipeline_trigger", "file_write"],
    },
    "kubernetes-mcp": {
        "id": "kubernetes-mcp",
        "display_name": "Kubernetes MCP",
        "url": os.environ.get("MCP_K8S_URL", "http://kubernetes-mcp.ai-portal.svc:8000"),
        "description": "Kubernetes cluster inspection and workload management",
        "capabilities": ["pod_list", "deploy_status", "log_fetch", "namespace_list"],
    },
    "postgres-mcp": {
        "id": "postgres-mcp",
        "display_name": "PostgreSQL MCP",
        "url": os.environ.get("MCP_POSTGRES_URL", "http://postgres-mcp.ai-portal.svc:8000"),
        "description": "Read-only SQL query execution and schema inspection",
        "capabilities": ["query_execute", "schema_inspect"],
    },
    "jira-mcp": {
        "id": "jira-mcp",
        "display_name": "Jira MCP",
        "url": os.environ.get("MCP_JIRA_URL", "http://jira-mcp.ai-portal.svc:8000"),
        "description": "Jira issue management and sprint operations",
        "capabilities": ["issue_read", "issue_create", "sprint_list"],
    },
    "vault-mcp": {
        "id": "vault-mcp",
        "display_name": "Vault MCP",
        "url": os.environ.get("MCP_VAULT_URL", "http://vault-mcp.ai-portal.svc:8000"),
        "description": "Read-only secret path listing and metadata inspection",
        "capabilities": ["secret_list", "secret_metadata"],
    },
    "harbor-mcp": {
        "id": "harbor-mcp",
        "display_name": "Harbor MCP",
        "url": os.environ.get("MCP_HARBOR_URL", "http://harbor-mcp.ai-portal.svc:8000"),
        "description": "Container image and vulnerability scan results from Harbor",
        "capabilities": ["image_list", "vulnerability_report"],
    },
    "confluence-mcp": {
        "id": "confluence-mcp",
        "display_name": "Confluence MCP",
        "url": os.environ.get("MCP_CONFLUENCE_URL", "http://confluence-mcp.ai-portal.svc:8000"),
        "description": "Read and write Confluence pages and spaces",
        "capabilities": ["page_read", "page_create", "space_list"],
    },
}


class McpServerEntry(BaseModel):
    id: str
    display_name: str
    url: str
    description: str
    capabilities: list[str]
    healthy: Optional[bool] = None


@app.get("/api/mcp-servers", response_model=list[McpServerEntry])
async def list_servers(check_health: bool = False):
    entries = [McpServerEntry(**v) for v in _REGISTRY.values()]
    if check_health:
        async with httpx.AsyncClient(timeout=3) as client:
            for entry in entries:
                try:
                    r = await client.get(f"{entry.url}/health/live")
                    entry.healthy = r.status_code == 200
                except Exception:
                    entry.healthy = False
    return entries


@app.get("/api/mcp-servers/{server_id}", response_model=McpServerEntry)
async def get_server(server_id: str):
    if server_id not in _REGISTRY:
        raise HTTPException(404, detail="Server not found")
    return McpServerEntry(**_REGISTRY[server_id])


@app.post("/api/mcp-servers/{server_id}/invoke/{tool_name}")
async def invoke_tool(server_id: str, tool_name: str, body: dict):
    if server_id not in _REGISTRY:
        raise HTTPException(404)
    url = f"{_REGISTRY[server_id]['url']}/tools/{tool_name}"
    async with httpx.AsyncClient(timeout=30) as client:
        resp = await client.post(url, json=body)
    return resp.json()


@app.get("/health/live")
async def health():
    return {"status": "ok"}
