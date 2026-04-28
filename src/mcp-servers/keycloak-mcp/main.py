"""Keycloak MCP Server — identity and access management tools."""
from __future__ import annotations

import os
import sys
import httpx
import uvicorn

sys.path.insert(0, str(__import__("pathlib").Path(__file__).parent.parent))
from shared.mcp_base import McpServer

KEYCLOAK_URL    = os.environ.get("KEYCLOAK_URL", "https://auth.ai.adports.ae")
KEYCLOAK_REALM  = os.environ.get("KEYCLOAK_REALM", "ai-portal")
ADMIN_TOKEN_URL = f"{KEYCLOAK_URL}/realms/master/protocol/openid-connect/token"
ADMIN_CLIENT_ID = os.environ.get("KEYCLOAK_ADMIN_CLIENT_ID", "admin-cli")
ADMIN_SECRET    = os.environ.get("KEYCLOAK_ADMIN_SECRET", "")

server = McpServer(title="Keycloak MCP", version="1.0.0")


async def _admin_token() -> str:
    async with httpx.AsyncClient() as client:
        r = await client.post(ADMIN_TOKEN_URL, data={
            "grant_type": "client_credentials",
            "client_id": ADMIN_CLIENT_ID,
            "client_secret": ADMIN_SECRET,
        })
        r.raise_for_status()
        return r.json()["access_token"]


@server.tool(
    name="list_users",
    description="List users in the ai-portal realm",
    input_schema={
        "type": "object",
        "properties": {
            "search": {"type": "string", "description": "Username/email search filter"},
            "max": {"type": "integer", "description": "Max results", "default": 20},
        }
    }
)
async def list_users(search: str = "", max: int = 20):
    token = await _admin_token()
    url = f"{KEYCLOAK_URL}/admin/realms/{KEYCLOAK_REALM}/users"
    params = {"max": max}
    if search:
        params["search"] = search
    async with httpx.AsyncClient() as client:
        r = await client.get(url, headers={"Authorization": f"Bearer {token}"}, params=params)
        r.raise_for_status()
    return r.json()


@server.tool(
    name="get_user_roles",
    description="Get realm roles assigned to a user",
    input_schema={
        "type": "object",
        "required": ["user_id"],
        "properties": {"user_id": {"type": "string"}}
    }
)
async def get_user_roles(user_id: str):
    token = await _admin_token()
    url = f"{KEYCLOAK_URL}/admin/realms/{KEYCLOAK_REALM}/users/{user_id}/role-mappings/realm"
    async with httpx.AsyncClient() as client:
        r = await client.get(url, headers={"Authorization": f"Bearer {token}"})
        r.raise_for_status()
    return r.json()


@server.tool(
    name="introspect_token",
    description="Introspect a bearer token and return claims",
    input_schema={
        "type": "object",
        "required": ["token"],
        "properties": {"token": {"type": "string"}}
    }
)
async def introspect_token(token: str):
    url = f"{KEYCLOAK_URL}/realms/{KEYCLOAK_REALM}/protocol/openid-connect/token/introspect"
    async with httpx.AsyncClient() as client:
        r = await client.post(url, data={
            "token": token,
            "client_id": ADMIN_CLIENT_ID,
            "client_secret": ADMIN_SECRET,
        })
        r.raise_for_status()
    return r.json()


app = server.app

if __name__ == "__main__":
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=False)
