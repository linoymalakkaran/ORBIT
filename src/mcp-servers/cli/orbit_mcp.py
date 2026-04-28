"""orbit-mcp CLI — invoke MCP tools from the command line."""
from __future__ import annotations

import argparse
import json
import os
import sys
import httpx


def main():
    parser = argparse.ArgumentParser(prog="orbit-mcp", description="ORBIT MCP CLI")
    parser.add_argument("--registry", default=os.environ.get("MCP_REGISTRY_URL", "http://localhost:8080"), help="MCP Registry base URL")
    parser.add_argument("--token", default=os.environ.get("ORBIT_TOKEN", ""), help="Bearer token")
    sub = parser.add_subparsers(dest="cmd")

    sub.add_parser("list-servers", help="List registered MCP servers")

    inv = sub.add_parser("invoke", help="Invoke a tool on an MCP server")
    inv.add_argument("server", help="MCP server id (e.g. gitlab-mcp)")
    inv.add_argument("tool", help="Tool name")
    inv.add_argument("--args", default="{}", help="JSON arguments")

    list_tools = sub.add_parser("list-tools", help="List tools of an MCP server")
    list_tools.add_argument("server", help="MCP server id")

    args = parser.parse_args()
    headers = {"Authorization": f"Bearer {args.token}"} if args.token else {}

    if args.cmd == "list-servers":
        resp = httpx.get(f"{args.registry}/api/mcp-servers", headers=headers)
        resp.raise_for_status()
        for s in resp.json():
            print(f"  {s['id']:20s}  {s['url']:50s}  {s['description'][:60]}")

    elif args.cmd == "list-tools":
        registry_resp = httpx.get(f"{args.registry}/api/mcp-servers/{args.server}", headers=headers)
        registry_resp.raise_for_status()
        server_url = registry_resp.json()["url"]
        resp = httpx.get(f"{server_url}/tools", headers=headers)
        resp.raise_for_status()
        for t in resp.json():
            print(f"  {t['name']:30s}  {t['description'][:70]}")

    elif args.cmd == "invoke":
        arguments = json.loads(args.args)
        resp = httpx.post(
            f"{args.registry}/api/mcp-servers/{args.server}/invoke/{args.tool}",
            json=arguments, headers=headers, timeout=30
        )
        resp.raise_for_status()
        print(json.dumps(resp.json(), indent=2))

    else:
        parser.print_help()
        sys.exit(1)


if __name__ == "__main__":
    main()
