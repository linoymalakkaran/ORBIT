# Phase 08 — MCP Server Foundation

## Summary

Build the foundational MCP (Model Context Protocol) server infrastructure that makes the AI Portal consumable from **any MCP-aware AI tool** — GitHub Copilot, Cursor, Claude Code, or any IDE that supports MCP. Phase 08 delivers the three most critical MCP servers: Keycloak, GitLab/Azure DevOps, and the MCP Registry itself. Every subsequent phase adds more MCP servers.

---

## Objectives

1. Establish the MCP server framework (shared Python FastAPI base with auth middleware).
2. Implement the MCP Registry API (catalog of all MCP servers with their tools).
3. Implement the **Keycloak MCP Server** (the most universally needed integration).
4. Implement the **GitLab/Azure DevOps MCP Server** (create repos, run pipelines).
5. Implement IDE connection guide (one-click config snippets for Copilot/Cursor/Claude Code).
6. Implement the `adports-ai` CLI skeleton (foundation for Phase 09+).
7. Document all MCP server schemas with examples.
8. Implement MCP server health monitoring (each server exposes a health endpoint).
9. Implement MCP server authentication (Keycloak OIDC — same as Portal).
10. Write developer onboarding guide for MCP setup.

---

## Prerequisites

- Phase 07 (Capability Fabric — Standards MCP server pattern established).
- Phase 01 (AKS, Keycloak, GitLab/Azure DevOps credentials in Vault).
- Keycloak admin API credentials in Vault.
- GitLab API token and/or Azure DevOps PAT in Vault.

---

## Duration

**2 weeks**

**Squad:** Fabric Squad (1 senior .NET + 1 Python engineer)

---

## Deliverables

| # | Deliverable | Acceptance Criterion |
|---|------------|---------------------|
| D1 | MCP server base framework | Auth middleware, health endpoint, error handling, OTEL tracing |
| D2 | MCP Registry API | `GET /api/mcps` returns all registered servers with tool catalogs |
| D3 | Keycloak MCP server | All 8 tools respond correctly; tested against dev Keycloak |
| D4 | GitLab/Azure DevOps MCP server | All 7 tools respond; project created via MCP visible in GitLab |
| D5 | IDE connection guide | One-click config snippet generated per IDE type |
| D6 | `adports-ai` CLI skeleton | `adports-ai --version` + `adports-ai mcps list` work |
| D7 | MCP server API documentation | OpenAPI spec for each server's tool endpoints |
| D8 | MCP health monitoring | Each server health endpoint hooked into Service Health Monitor |
| D9 | MCP authentication | Tools require valid Portal JWT; unauthorized calls rejected |
| D10 | Developer onboarding guide | Step-by-step guide tested by a developer unfamiliar with MCP |

---

## MCP Server Base Framework

All MCP servers share a common Python base:

```python
# shared/mcp_base.py
from mcp import McpServer
from fastapi import FastAPI, Depends, HTTPException
from fastapi.security import OAuth2PasswordBearer
import httpx
import opentelemetry

class AdPortsMcpBase:
    def __init__(self, server_id: str, display_name: str):
        self.server_id = server_id
        self.app = FastAPI(title=f"AD Ports MCP — {display_name}")
        self.mcp = McpServer(server_id)
        self._setup_auth()
        self._setup_health()
        self._setup_telemetry()

    def _setup_auth(self):
        """Validate Keycloak JWT on every tool call."""
        oauth2_scheme = OAuth2PasswordBearer(tokenUrl="token")
        @self.app.middleware("http")
        async def verify_token(request, call_next):
            token = request.headers.get("Authorization", "").removeprefix("Bearer ")
            if not token:
                raise HTTPException(status_code=401, detail="Missing token")
            # Verify against Keycloak JWKS
            claims = await verify_keycloak_jwt(token)
            request.state.user = claims
            return await call_next(request)

    def _setup_health(self):
        @self.app.get("/health/live")
        async def live(): return {"status": "ok"}

        @self.app.get("/health/ready")
        async def ready(): return await self.check_ready()

    async def check_ready(self) -> dict:
        """Override in subclasses to check backing service connectivity."""
        return {"status": "ok"}
```

---

## Keycloak MCP Server

```python
# servers/keycloak/main.py
from shared.mcp_base import AdPortsMcpBase
from keycloak import KeycloakAdmin

server = AdPortsMcpBase("adports-keycloak", "Keycloak Identity")

@server.mcp.tool("list_realms")
async def list_realms(ctx) -> list[dict]:
    """List all Keycloak realms visible to the caller."""
    admin = get_keycloak_admin(ctx)
    return admin.get_realms()

@server.mcp.tool("get_realm")
async def get_realm(realm_name: str, ctx) -> dict:
    """Get full configuration of a Keycloak realm."""
    admin = get_keycloak_admin(ctx)
    return admin.get_realm(realm_name)

@server.mcp.tool("create_client")
async def create_client(realm: str, client_config: dict, ctx) -> dict:
    """Create an OIDC or SAML client in the specified realm."""
    require_permission(ctx, "keycloak:write")
    admin = get_keycloak_admin(ctx)
    validate_against_spec(client_config, "adports-keycloak-client.schema.json")
    client_id = admin.create_client(realm, client_config)
    record_ledger_event("keycloak.client.created", {"realm": realm, "client": client_id})
    return {"client_id": client_id, "realm": realm}

@server.mcp.tool("add_realm_role")
async def add_realm_role(realm: str, role_name: str, description: str, ctx) -> dict:
    """Add a new realm role."""
    require_permission(ctx, "keycloak:write")
    admin = get_keycloak_admin(ctx)
    admin.create_realm_role(realm, {"name": role_name, "description": description})
    return {"created": True}

@server.mcp.tool("configure_group")
async def configure_group(realm: str, group_config: dict, ctx) -> dict:
    """Create or update a group with roles and attributes."""
    require_permission(ctx, "keycloak:write")
    admin = get_keycloak_admin(ctx)
    return admin.create_group(realm, group_config)

@server.mcp.tool("export_realm_json")
async def export_realm_json(realm: str, ctx) -> dict:
    """Export full realm configuration as JSON (for GitOps backup)."""
    admin = get_keycloak_admin(ctx)
    return admin.export_realm(realm)

@server.mcp.tool("get_client_secret")
async def get_client_secret(realm: str, client_id: str, ctx) -> str:
    """Retrieve the client secret (stored in Vault, not directly from Keycloak)."""
    require_permission(ctx, "keycloak:secrets")
    return await vault_service.get_secret(f"keycloak/{realm}/clients/{client_id}/secret")

@server.mcp.tool("validate_realm_against_spec")
async def validate_realm_config(realm: str, ctx) -> dict:
    """Validate current realm configuration against AD Ports standard spec."""
    admin = get_keycloak_admin(ctx)
    realm_json = admin.get_realm(realm)
    return validate_against_spec(realm_json, "adports-keycloak-realm.schema.json")
```

---

## GitLab/Azure DevOps MCP Server

```python
@server.mcp.tool("create_project")
async def create_project(group_path: str, project_name: str, template: str, ctx) -> dict:
    """Create a new GitLab project (or Azure DevOps project) from an AD Ports template."""
    require_permission(ctx, "vcs:write")
    require_hook_pass("pre-project-create", {"group": group_path, "name": project_name})
    result = await gitlab_api.create_project(group_path, project_name, template)
    record_ledger_event("project.repo.created", result)
    return result

@server.mcp.tool("protect_branch")
async def protect_branch(project_path: str, branch: str, rules: dict, ctx) -> dict:
    """Protect a branch with push/merge rules."""

@server.mcp.tool("add_project_variable")
async def add_project_variable(project_path: str, key: str, value: str, masked: bool, ctx) -> dict:
    """Add a CI/CD variable to a project (masked secrets come from Vault)."""

@server.mcp.tool("run_pipeline")
async def run_pipeline(project_path: str, ref: str, variables: dict, ctx) -> dict:
    """Trigger a pipeline run and return the pipeline ID."""

@server.mcp.tool("get_pipeline_logs")
async def get_pipeline_logs(project_path: str, pipeline_id: int, job_name: str, ctx) -> str:
    """Retrieve logs from a specific pipeline job."""

@server.mcp.tool("create_merge_request")
async def create_merge_request(project_path: str, source_branch: str,
                                target_branch: str, title: str, description: str, ctx) -> dict:
    """Create a merge/pull request."""

@server.mcp.tool("list_pipelines")
async def list_pipelines(project_path: str, status: str | None, ctx) -> list[dict]:
    """List recent pipelines for a project."""
```

---

## MCP Registry API

```http
GET /api/mcps
→ [
    {
      "id": "adports-keycloak",
      "display_name": "Keycloak Identity",
      "description": "Create and manage Keycloak realms, clients, roles, groups",
      "url": "https://mcp.adports-ai.internal/keycloak",
      "status": "healthy",
      "tools": [ { "name": "list_realms", "description": "..." }, ... ],
      "auth": "keycloak-bearer",
      "required_roles": ["keycloak:read"],
      "ide_config_snippet": {
        "vscode_copilot": "...",
        "cursor": "...",
        "claude_code": "..."
      }
    }
  ]
```

The `ide_config_snippet` enables the Portal UI to show a "Connect from your IDE" button that generates a copy-paste config for the developer's IDE.

---

## IDE Connection Guide (Generated Config Snippets)

### VS Code / GitHub Copilot

```json
// .vscode/settings.json
{
  "github.copilot.chat.mcp": {
    "servers": {
      "adports-keycloak": {
        "url": "https://mcp.adports-ai.internal/keycloak",
        "auth": { "type": "bearer", "tokenProvider": "keycloak" }
      },
      "adports-gitlab": {
        "url": "https://mcp.adports-ai.internal/gitlab"
      },
      "adports-standards": {
        "url": "https://mcp.adports-ai.internal/standards"
      }
    }
  }
}
```

### Cursor

```json
// cursor/mcp_servers.json
{
  "adports-keycloak": {
    "command": "npx",
    "args": ["@adports/mcp-proxy", "--url", "https://mcp.adports-ai.internal/keycloak"],
    "env": { "ADPORTS_MCP_TOKEN": "${ADPORTS_TOKEN}" }
  }
}
```

---

## `adports-ai` CLI Skeleton

```bash
# Initial commands in CLI skeleton
adports-ai --version            # 0.1.0
adports-ai mcps list            # List available MCP servers
adports-ai mcps status          # Health of all MCP servers
adports-ai login                # Authenticate with Portal (Keycloak flow)
adports-ai logout               # Clear credentials
adports-ai whoami               # Show current user + roles
```

Built with Node.js + Commander.js. Distributed via:
- `npm install -g @adports/ai-cli`
- `winget install ADPorts.AI`

---

## Step-by-Step Execution Plan

### Week 1: Framework + Keycloak MCP

- [ ] Implement MCP server base framework (auth, health, OTEL).
- [ ] Implement MCP Registry API and Portal Admin UI section.
- [ ] Implement Keycloak MCP server (8 tools).
- [ ] Deploy Keycloak MCP to AKS.
- [ ] Test all 8 Keycloak tools from Cursor.

### Week 2: GitLab MCP + CLI + Guides

- [ ] Implement GitLab/Azure DevOps MCP server (7 tools).
- [ ] Deploy GitLab MCP to AKS.
- [ ] Implement `adports-ai` CLI skeleton.
- [ ] Publish CLI to npm registry.
- [ ] Write IDE connection guide with tested config snippets.
- [ ] Write developer onboarding guide (tested with a fresh developer).
- [ ] MCP health endpoints hooked into Health Monitor (Phase 20 pre-wiring).

---

## Gate Criterion

- All 10 deliverables pass acceptance criteria.
- All 8 Keycloak MCP tools respond correctly from Cursor and Copilot.
- All 7 GitLab/Azure DevOps tools respond correctly.
- `adports-ai mcps list` returns all registered servers.
- IDE connection guide tested by 2 developers new to MCP — successful in < 10 minutes.

---

*Phase 08 — MCP Server Foundation — AI Portal — v1.0*
