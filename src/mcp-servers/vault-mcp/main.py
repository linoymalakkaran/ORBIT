"""Vault MCP Server — read-only secret metadata and path listing."""
from __future__ import annotations

import os
import sys
import httpx
import uvicorn

sys.path.insert(0, str(__import__("pathlib").Path(__file__).parent.parent))
from shared.mcp_base import McpServer

VAULT_ADDR  = os.environ.get("VAULT_ADDR", "http://vault.ai-portal-vault.svc.cluster.local:8200")
VAULT_TOKEN = os.environ.get("VAULT_TOKEN", "")

server = McpServer(title="Vault MCP", version="1.0.0")


def _headers() -> dict:
    return {"X-Vault-Token": VAULT_TOKEN}


@server.tool(
    name="list_secret_paths",
    description="List secret keys at a Vault path (metadata only, no values)",
    input_schema={
        "type": "object",
        "required": ["path"],
        "properties": {"path": {"type": "string", "description": "e.g. 'secret/data/pipeline-ledger'"}}
    }
)
async def list_secret_paths(path: str):
    # Use LIST verb on the metadata path
    meta_path = path.replace("secret/data/", "secret/metadata/")
    async with httpx.AsyncClient() as client:
        r = await client.request("LIST", f"{VAULT_ADDR}/v1/{meta_path}", headers=_headers())
        r.raise_for_status()
    return r.json()


@server.tool(
    name="get_secret_metadata",
    description="Get Vault secret metadata (version info, creation time) without revealing values",
    input_schema={
        "type": "object",
        "required": ["path"],
        "properties": {"path": {"type": "string"}}
    }
)
async def get_secret_metadata(path: str):
    meta_path = path.replace("secret/data/", "secret/metadata/")
    async with httpx.AsyncClient() as client:
        r = await client.get(f"{VAULT_ADDR}/v1/{meta_path}", headers=_headers())
        r.raise_for_status()
    data = r.json()
    # Strip secret values from response — only return metadata
    data.pop("data", None)
    return data


app = server.app
if __name__ == "__main__":
    uvicorn.run("main:app", host="0.0.0.0", port=8000)
