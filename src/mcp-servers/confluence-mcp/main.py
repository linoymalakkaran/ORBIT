"""Confluence MCP Server — wiki page read/write tools."""
from __future__ import annotations

import os
import sys
import httpx
import uvicorn

sys.path.insert(0, str(__import__("pathlib").Path(__file__).parent.parent))
from shared.mcp_base import McpServer

CONFLUENCE_URL   = os.environ.get("CONFLUENCE_URL", "https://wiki.adports.ae")
CONFLUENCE_TOKEN = os.environ.get("CONFLUENCE_TOKEN", "")
_headers = {"Authorization": f"Bearer {CONFLUENCE_TOKEN}", "Content-Type": "application/json"}

server = McpServer(title="Confluence MCP", version="1.0.0")


@server.tool(
    name="get_page",
    description="Retrieve a Confluence page by ID",
    input_schema={
        "type": "object",
        "required": ["page_id"],
        "properties": {"page_id": {"type": "string"}}
    }
)
async def get_page(page_id: str):
    url = f"{CONFLUENCE_URL}/wiki/rest/api/content/{page_id}?expand=body.storage"
    async with httpx.AsyncClient() as client:
        r = await client.get(url, headers=_headers)
        r.raise_for_status()
    return r.json()


@server.tool(
    name="search_pages",
    description="Search Confluence pages using CQL",
    input_schema={
        "type": "object",
        "required": ["cql"],
        "properties": {
            "cql": {"type": "string", "description": "Confluence Query Language expression"},
            "limit": {"type": "integer", "default": 10},
        }
    }
)
async def search_pages(cql: str, limit: int = 10):
    url = f"{CONFLUENCE_URL}/wiki/rest/api/content/search"
    async with httpx.AsyncClient() as client:
        r = await client.get(url, headers=_headers, params={"cql": cql, "limit": limit})
        r.raise_for_status()
    return r.json()


@server.tool(
    name="create_page",
    description="Create a new Confluence page",
    input_schema={
        "type": "object",
        "required": ["space_key", "title", "body_html"],
        "properties": {
            "space_key": {"type": "string"},
            "title": {"type": "string"},
            "body_html": {"type": "string"},
            "parent_id": {"type": "string", "default": ""},
        }
    }
)
async def create_page(space_key: str, title: str, body_html: str, parent_id: str = ""):
    payload: dict = {
        "type": "page",
        "title": title,
        "space": {"key": space_key},
        "body": {"storage": {"value": body_html, "representation": "storage"}},
    }
    if parent_id:
        payload["ancestors"] = [{"id": parent_id}]
    async with httpx.AsyncClient() as client:
        r = await client.post(f"{CONFLUENCE_URL}/wiki/rest/api/content", headers=_headers, json=payload)
        r.raise_for_status()
    return r.json()


app = server.app
if __name__ == "__main__":
    uvicorn.run("main:app", host="0.0.0.0", port=8000)
