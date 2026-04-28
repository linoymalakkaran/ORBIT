"""MCP base server framework — all ORBIT MCP servers inherit from McpServer."""
from __future__ import annotations

import logging
from typing import Any, Callable, Optional

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from pydantic import BaseModel

logger = logging.getLogger(__name__)


class ToolDefinition(BaseModel):
    name: str
    description: str
    input_schema: dict  # JSON Schema


class ToolCall(BaseModel):
    tool: str
    arguments: dict = {}


class ToolResult(BaseModel):
    tool: str
    result: Any
    error: Optional[str] = None


class McpServer:
    """
    Base class for all ORBIT MCP servers.
    Each subclass registers tools via @server.tool(name, description, schema).
    Exposes:
      GET  /tools            — list available tools
      POST /tools/{name}     — invoke a tool
      GET  /health/live      — liveness
    """

    def __init__(self, title: str, version: str = "1.0.0"):
        self.app = FastAPI(title=title, version=version, docs_url="/docs")
        self._tools: dict[str, tuple[ToolDefinition, Callable]] = {}
        self._setup_routes()

    def tool(self, name: str, description: str, input_schema: dict):
        """Decorator to register a tool handler."""
        def decorator(fn: Callable):
            defn = ToolDefinition(name=name, description=description, input_schema=input_schema)
            self._tools[name] = (defn, fn)
            return fn
        return decorator

    def _setup_routes(self):
        @self.app.get("/tools")
        async def list_tools() -> list[dict]:
            return [defn.model_dump() for defn, _ in self._tools.values()]

        @self.app.post("/tools/{tool_name}")
        async def call_tool(tool_name: str, request: Request) -> JSONResponse:
            if tool_name not in self._tools:
                return JSONResponse({"error": f"Unknown tool: {tool_name}"}, status_code=404)
            defn, handler = self._tools[tool_name]
            body = await request.json()
            try:
                result = await handler(**body)
                return JSONResponse({"tool": tool_name, "result": result})
            except Exception as exc:
                logger.exception("Tool %s failed", tool_name)
                return JSONResponse({"tool": tool_name, "error": str(exc)}, status_code=500)

        @self.app.get("/health/live")
        async def health():
            return {"status": "ok"}
