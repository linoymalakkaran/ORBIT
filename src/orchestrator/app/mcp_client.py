"""MCP tool invocation client."""
from __future__ import annotations

import httpx
from app.config import settings


async def invoke_mcp_tool(server_id: str, tool_name: str, arguments: dict) -> dict:
    url = f"{settings.mcp_registry_url}/api/mcp-servers/{server_id}/invoke/{tool_name}"
    async with httpx.AsyncClient(timeout=30) as client:
        r = await client.post(url, json=arguments)
        r.raise_for_status()
    return r.json()
