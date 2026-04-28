"""PostgreSQL MCP Server — read-only query and schema inspection."""
from __future__ import annotations

import os
import sys
import asyncpg
import uvicorn

sys.path.insert(0, str(__import__("pathlib").Path(__file__).parent.parent))
from shared.mcp_base import McpServer

PG_DSN = os.environ.get("POSTGRES_MCP_DSN", "postgresql://readonly:changeme@postgres:5432/orbit")

server = McpServer(title="PostgreSQL MCP", version="1.0.0")

# Allowlist of safe statement prefixes (read-only guard)
_SAFE_PREFIXES = ("select ", "with ", "explain ")


def _is_safe(query: str) -> bool:
    return query.strip().lower().split()[0] in ("select", "with", "explain")


@server.tool(
    name="execute_query",
    description="Execute a read-only SQL query (SELECT / WITH / EXPLAIN only)",
    input_schema={
        "type": "object",
        "required": ["query"],
        "properties": {
            "query": {"type": "string"},
            "limit": {"type": "integer", "default": 100},
        }
    }
)
async def execute_query(query: str, limit: int = 100):
    if not _is_safe(query):
        raise ValueError("Only SELECT/WITH/EXPLAIN queries are permitted")
    # Wrap in a LIMIT if not already present
    safe_query = f"SELECT * FROM ({query}) _q LIMIT {min(limit, 500)}"
    conn = await asyncpg.connect(PG_DSN)
    try:
        rows = await conn.fetch(safe_query)
        return [dict(r) for r in rows]
    finally:
        await conn.close()


@server.tool(
    name="inspect_schema",
    description="List tables and columns in a PostgreSQL schema",
    input_schema={
        "type": "object",
        "properties": {
            "schema_name": {"type": "string", "default": "public"},
        }
    }
)
async def inspect_schema(schema_name: str = "public"):
    query = """
        SELECT table_name, column_name, data_type, is_nullable
        FROM information_schema.columns
        WHERE table_schema = $1
        ORDER BY table_name, ordinal_position
    """
    conn = await asyncpg.connect(PG_DSN)
    try:
        rows = await conn.fetch(query, schema_name)
        return [dict(r) for r in rows]
    finally:
        await conn.close()


app = server.app
if __name__ == "__main__":
    uvicorn.run("main:app", host="0.0.0.0", port=8000)
