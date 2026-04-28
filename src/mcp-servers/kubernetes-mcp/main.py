"""Kubernetes MCP Server — cluster inspection tools."""
from __future__ import annotations

import os
import sys
import subprocess
import json
import uvicorn

sys.path.insert(0, str(__import__("pathlib").Path(__file__).parent.parent))
from shared.mcp_base import McpServer

server = McpServer(title="Kubernetes MCP", version="1.0.0")

KUBECTL = os.environ.get("KUBECTL_PATH", "kubectl")


def _run(args: list[str]) -> dict:
    result = subprocess.run(
        [KUBECTL] + args + ["-o", "json"],
        capture_output=True, text=True, timeout=15
    )
    if result.returncode != 0:
        raise RuntimeError(result.stderr[:500])
    return json.loads(result.stdout)


@server.tool(
    name="list_pods",
    description="List pods in a namespace",
    input_schema={
        "type": "object",
        "properties": {
            "namespace": {"type": "string", "default": "ai-portal"},
            "label_selector": {"type": "string", "default": ""},
        }
    }
)
async def list_pods(namespace: str = "ai-portal", label_selector: str = ""):
    args = ["get", "pods", "-n", namespace]
    if label_selector:
        args += ["-l", label_selector]
    return _run(args)


@server.tool(
    name="get_deployment_status",
    description="Get status of a Deployment",
    input_schema={
        "type": "object",
        "required": ["name"],
        "properties": {
            "name": {"type": "string"},
            "namespace": {"type": "string", "default": "ai-portal"},
        }
    }
)
async def get_deployment_status(name: str, namespace: str = "ai-portal"):
    return _run(["get", "deployment", name, "-n", namespace])


@server.tool(
    name="get_pod_logs",
    description="Fetch recent logs from a pod",
    input_schema={
        "type": "object",
        "required": ["pod_name"],
        "properties": {
            "pod_name": {"type": "string"},
            "namespace": {"type": "string", "default": "ai-portal"},
            "tail_lines": {"type": "integer", "default": 100},
        }
    }
)
async def get_pod_logs(pod_name: str, namespace: str = "ai-portal", tail_lines: int = 100):
    result = subprocess.run(
        [KUBECTL, "logs", pod_name, "-n", namespace, f"--tail={tail_lines}"],
        capture_output=True, text=True, timeout=15
    )
    return {"pod": pod_name, "logs": result.stdout}


@server.tool(
    name="list_namespaces",
    description="List all namespaces in the cluster",
    input_schema={"type": "object", "properties": {}}
)
async def list_namespaces():
    return _run(["get", "namespaces"])


app = server.app
if __name__ == "__main__":
    uvicorn.run("main:app", host="0.0.0.0", port=8000)
