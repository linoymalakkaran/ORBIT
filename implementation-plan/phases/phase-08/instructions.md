# Instructions — Phase 08: MCP Server Foundation

> Add this file to your IDE's custom instructions when building MCP servers for the AD Ports AI Portal.

---

## Context

You are building **MCP (Model Context Protocol) servers** for the AD Ports AI Portal. Every MCP server follows the shared `AdPortsMcpBase` pattern and is deployed as a standalone FastAPI application on AKS. Tools must work identically whether called from GitHub Copilot, Cursor, Claude Code, or the Portal's own orchestrator.

---

## Python Project Structure

```
mcp-servers/
├── shared/
│   ├── mcp_base.py           ← AdPortsMcpBase (auth, health, telemetry)
│   ├── auth.py               ← Keycloak JWT verification
│   ├── ledger_client.py      ← Pipeline Ledger recording
│   ├── hook_engine_client.py ← Pre-action Hook Engine check
│   └── models.py             ← Shared Pydantic models
├── keycloak/
│   ├── server.py             ← Keycloak MCP server
│   ├── tools/                ← One file per tool
│   └── tests/
├── gitlab/
│   └── ...
└── helm/
    └── mcp-servers/
        └── templates/        ← One Deployment + Service per MCP server
```

## Tool Implementation Pattern

```python
# Every tool follows this exact pattern
from mcp import tool
from shared.mcp_base import AdPortsMcpBase, require_permission, require_hook_pass
from shared.ledger_client import LedgerClient

server = AdPortsMcpBase("keycloak-mcp", "AD Ports Keycloak MCP")


@server.tool("list_realms")
async def list_realms(ctx) -> list[dict]:
    """
    List all Keycloak realms.
    Requires: keycloak:read permission.
    """
    require_permission(ctx, "keycloak:read")
    # Tool implementation
    return await keycloak_admin.get_realms()


@server.tool("provision_realm")
async def provision_realm(
    realm_name: str,
    service_name: str,
    client_ids: list[str],
    roles: list[str],
    environment: str,
    ctx,
) -> dict:
    """
    Provision a new Keycloak realm for an AD Ports service.
    Requires: keycloak:write permission.
    Records: Pipeline Ledger event.
    """
    require_permission(ctx, "keycloak:write")

    # Pre-action Hook Engine check (mandatory for mutating tools)
    require_hook_pass("keycloak.provision_realm", {
        "realm_name": realm_name,
        "caller": ctx.caller,
    })

    # Validate against AD Ports schema before applying
    validate_realm_config({"realm": realm_name, "enabled": True, ...})

    result = await keycloak_admin.create_realm(realm_name, service_name, client_ids, roles)

    # Record to Pipeline Ledger (mandatory for mutating tools)
    await LedgerClient.record_event(
        event_type="keycloak.realm.provisioned",
        project_id=ctx.project_id,
        actor_id=ctx.caller["sub"],
        event_data={"realm_name": realm_name, "service_name": service_name},
    )

    return result
```

## Authentication Middleware

All MCP servers use the shared Keycloak JWT verification:

```python
# shared/auth.py
import httpx
from jose import jwt, JWTError
from functools import lru_cache


@lru_cache(maxsize=1)
def get_jwks() -> dict:
    """Cache JWKS for 1 hour — do not fetch on every request."""
    response = httpx.get(f"{KEYCLOAK_URL}/realms/portal/protocol/openid-connect/certs")
    response.raise_for_status()
    return response.json()


async def verify_portal_jwt(token: str) -> dict:
    """Verify a Keycloak Portal realm JWT. Returns claims dict."""
    try:
        claims = jwt.decode(
            token,
            get_jwks(),
            algorithms=["RS256"],
            audience="account",
            issuer=f"{KEYCLOAK_URL}/realms/portal",
        )
        return claims
    except JWTError as e:
        raise UnauthorizedException(f"Invalid token: {e}")
```

## IDE Configuration Generation

Every MCP server must generate IDE configuration snippets:

```python
# In server.py
def get_ide_configs(server_url: str) -> dict:
    return {
        "copilot": json.dumps({
            "github.copilot.chat.mcp.servers": {
                server.server_id: {
                    "url": f"{server_url}/mcp",
                    "description": server.display_name,
                }
            }
        }, indent=2),
        "cursor": json.dumps({
            "mcpServers": {
                server.server_id: {
                    "url": f"{server_url}/mcp",
                }
            }
        }, indent=2),
    }
```

## Hook Engine Integration

For any tool that mutates state, the Hook Engine check is MANDATORY:

```python
from shared.hook_engine_client import HookEngineClient

async def require_hook_pass(action_type: str, context: dict, caller: dict) -> None:
    """Raise ForbiddenError if Hook Engine denies the action."""
    result = await HookEngineClient.evaluate({
        "action": {"type": action_type, "context": context},
        "caller": caller,
        "project": {"id": context.get("project_id", "unknown")},
    })
    if not result["allow"]:
        reasons = "; ".join(result["deny"])
        raise ForbiddenOperationError(f"Action denied by Hook Engine: {reasons}")
```

## Testing Requirements

```python
# Every tool must have unit tests with mocked backing service
@pytest.mark.asyncio
async def test_list_realms_requires_permission():
    ctx = MockContext(roles=["developer"])  # Missing keycloak:read
    with pytest.raises(ForbiddenError):
        await list_realms(ctx)

async def test_provision_realm_records_ledger_event():
    ctx = MockContext(roles=["platform_admin"])
    with patch("ledger_client.record_event") as mock_ledger:
        await provision_realm("test-realm", "Test Service", ["test-ui"], ["operator"], "dev", ctx)
        mock_ledger.assert_called_once()
```

## Forbidden Patterns

| Pattern | Reason |
|---------|--------|
| Storing backing-service credentials in tool code | Use Vault — credentials rotate |
| Skipping Hook Engine check for mutating tools | Policy bypass — mandatory for all state-changing tools |
| Skipping Pipeline Ledger for mutating tools | Audit gap — every write must be recorded |
| Catching all exceptions and returning `{}` | Errors must propagate so callers know the tool failed |
| Hardcoding `localhost` URLs | Tools run in AKS — use service DNS names |
| Non-idempotent create operations | Tools may be retried — `provision_realm` must check if realm exists first |

---

*Instructions — Phase 08 — AD Ports AI Portal — Applies to: Fabric Squad*
