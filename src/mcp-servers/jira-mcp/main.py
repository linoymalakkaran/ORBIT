"""Jira MCP Server — issue and sprint management."""
from __future__ import annotations

import os
import sys
import httpx
import uvicorn

sys.path.insert(0, str(__import__("pathlib").Path(__file__).parent.parent))
from shared.mcp_base import McpServer

JIRA_URL   = os.environ.get("JIRA_URL", "https://jira.adports.ae")
JIRA_TOKEN = os.environ.get("JIRA_TOKEN", "")
_headers   = {"Authorization": f"Bearer {JIRA_TOKEN}", "Content-Type": "application/json"}

server = McpServer(title="Jira MCP", version="1.0.0")


@server.tool(
    name="search_issues",
    description="Search Jira issues using JQL",
    input_schema={
        "type": "object",
        "required": ["jql"],
        "properties": {
            "jql": {"type": "string"},
            "max_results": {"type": "integer", "default": 20},
        }
    }
)
async def search_issues(jql: str, max_results: int = 20):
    async with httpx.AsyncClient() as client:
        r = await client.post(
            f"{JIRA_URL}/rest/api/3/issue/search",
            headers=_headers,
            json={"jql": jql, "maxResults": max_results, "fields": ["summary", "status", "assignee", "priority"]},
        )
        r.raise_for_status()
    return r.json()


@server.tool(
    name="create_issue",
    description="Create a new Jira issue",
    input_schema={
        "type": "object",
        "required": ["project_key", "summary", "issue_type"],
        "properties": {
            "project_key": {"type": "string"},
            "summary": {"type": "string"},
            "issue_type": {"type": "string", "description": "'Story' | 'Bug' | 'Task'"},
            "description": {"type": "string", "default": ""},
            "priority": {"type": "string", "default": "Medium"},
        }
    }
)
async def create_issue(project_key: str, summary: str, issue_type: str,
                       description: str = "", priority: str = "Medium"):
    payload = {
        "fields": {
            "project": {"key": project_key},
            "summary": summary,
            "issuetype": {"name": issue_type},
            "priority": {"name": priority},
            "description": {
                "type": "doc", "version": 1,
                "content": [{"type": "paragraph", "content": [{"type": "text", "text": description}]}]
            },
        }
    }
    async with httpx.AsyncClient() as client:
        r = await client.post(f"{JIRA_URL}/rest/api/3/issue", headers=_headers, json=payload)
        r.raise_for_status()
    return r.json()


@server.tool(
    name="list_sprints",
    description="List sprints for a Jira board",
    input_schema={
        "type": "object",
        "required": ["board_id"],
        "properties": {
            "board_id": {"type": "integer"},
            "state": {"type": "string", "default": "active"},
        }
    }
)
async def list_sprints(board_id: int, state: str = "active"):
    async with httpx.AsyncClient() as client:
        r = await client.get(
            f"{JIRA_URL}/rest/agile/1.0/board/{board_id}/sprint",
            headers=_headers, params={"state": state}
        )
        r.raise_for_status()
    return r.json()


app = server.app
if __name__ == "__main__":
    uvicorn.run("main:app", host="0.0.0.0", port=8000)
