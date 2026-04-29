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


@server.tool(
    name="transition_issue",
    description="Transition a Jira issue to a new workflow status (e.g. 'In Review', 'Done')",
    input_schema={
        "type": "object",
        "required": ["issue_key", "transition"],
        "properties": {
            "issue_key":  {"type": "string", "description": "Jira issue key, e.g. ORBIT-123"},
            "transition": {"type": "string", "description": "Target status name, e.g. 'In Review'"},
        }
    }
)
async def transition_issue(issue_key: str, transition: str):
    """Transitions a Jira issue to the named workflow status.

    Looks up the available transitions for the issue, finds the one whose
    name matches (case-insensitive), and POSTs the transition.
    """
    async with httpx.AsyncClient() as client:
        # 1. Get available transitions
        r = await client.get(
            f"{JIRA_URL}/rest/api/3/issue/{issue_key}/transitions",
            headers=_headers,
        )
        r.raise_for_status()
        transitions = r.json().get("transitions", [])
        match = next(
            (t for t in transitions if t["name"].lower() == transition.lower()),
            None,
        )
        if not match:
            available = [t["name"] for t in transitions]
            raise ValueError(
                f"Transition '{transition}' not found for {issue_key}. "
                f"Available: {available}"
            )
        # 2. Execute the transition
        r2 = await client.post(
            f"{JIRA_URL}/rest/api/3/issue/{issue_key}/transitions",
            headers=_headers,
            json={"transition": {"id": match["id"]}},
        )
        r2.raise_for_status()
    return {"issue_key": issue_key, "transitioned_to": transition, "transition_id": match["id"]}


app = server.app
if __name__ == "__main__":
    uvicorn.run("main:app", host="0.0.0.0", port=8000)
