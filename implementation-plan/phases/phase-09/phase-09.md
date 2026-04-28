# Phase 09 — Additional MCP Servers

## Summary

Implement the remaining MCP servers that power specialist agents and enable deep developer productivity from IDEs. By the end of this phase, the Portal exposes 9 additional domain-specific MCP servers covering infrastructure, data, security, project management, testing, and monitoring — bringing the total to 12+ servers.

---

## Objectives

1. **AKS MCP Server** — Kubernetes operations (namespace, Helm, pod logs).
2. **PostgreSQL MCP Server** — Database operations (create DB, apply migration, schema diff).
3. **Jira MCP Server** — Work item management (create epic/story, transition, link commits).
4. **Azure Boards MCP Server** — Azure DevOps work items (same patterns as Jira).
5. **SonarQube MCP Server** — Code quality (quality gate status, issues, analysis trigger).
6. **Checkmarx MCP Server** — SAST (trigger scan, fetch findings, manage presets).
7. **Vault MCP Server** — Secrets (read secret path, rotate credential, list grants).
8. **Postman/Newman MCP Server** — Integration tests (generate collection, run, get report).
9. **Draw.io MCP Server** — Architecture diagrams (generate from component list, export).
10. Extend `adports-ai` CLI with domain-specific commands for each new server.

---

## Prerequisites

- Phase 08 (MCP base framework, Registry, CLI skeleton).
- Phase 01 (AKS credentials, Vault, SonarQube, Checkmarx in Vault).
- Jira API token / Azure DevOps PAT in Vault.
- SonarQube + Checkmarx instances accessible.

---

## Duration

**3 weeks** (3 engineers in parallel — 3 servers each)

**Squad:** Fabric Squad (Python engineer × 3)

---

## Deliverables

| # | MCP Server | Key Tools | Acceptance Criterion |
|---|-----------|----------|---------------------|
| D1 | AKS MCP | 6 tools | Helm chart deployed via MCP; pod logs retrieved |
| D2 | PostgreSQL MCP | 6 tools | New DB created via MCP; migration applied |
| D3 | Jira MCP | 7 tools | Epic + stories created and linked via MCP |
| D4 | Azure Boards MCP | 6 tools | Work items created in Azure DevOps |
| D5 | SonarQube MCP | 5 tools | Quality gate status returned; analysis triggered |
| D6 | Checkmarx MCP | 5 tools | SAST scan triggered; findings returned |
| D7 | Vault MCP | 5 tools | Secret read via MCP; rotation recorded in Ledger |
| D8 | Postman/Newman MCP | 6 tools | Collection run against staging; report returned |
| D9 | Draw.io MCP | 4 tools | Architecture diagram generated from component list |
| D10 | CLI extensions | All domains | All new commands work from terminal + IDE |

---

## AKS MCP Server — Tool Catalog

```python
@server.mcp.tool("list_namespaces")
async def list_namespaces(cluster: str, ctx) -> list[dict]:
    """List AKS namespaces with resource quotas."""

@server.mcp.tool("apply_helm_chart")
async def apply_helm_chart(namespace: str, chart: str, values: dict, ctx) -> dict:
    """Apply a Helm chart to an AKS namespace (requires infra:write permission)."""
    require_permission(ctx, "infra:write")
    require_hook_pass("pre-helm-apply", {"namespace": namespace, "chart": chart})
    result = await helm.upgrade_install(namespace, chart, values)
    record_ledger_event("infra.helm.applied", result)
    return result

@server.mcp.tool("get_pod_logs")
async def get_pod_logs(namespace: str, pod_selector: str, tail_lines: int = 100, ctx) -> str:
    """Get logs from a pod or deployment."""

@server.mcp.tool("describe_pod")
async def describe_pod(namespace: str, pod_name: str, ctx) -> dict:
    """Get full pod description including events and resource usage."""

@server.mcp.tool("restart_deployment")
async def restart_deployment(namespace: str, deployment_name: str, ctx) -> dict:
    """Rolling restart a deployment (opt-in auto-remediation)."""
    require_permission(ctx, "infra:restart")
    require_hook_pass("pre-pod-restart", {"namespace": namespace, "deployment": deployment_name})

@server.mcp.tool("get_helm_release_status")
async def get_helm_release_status(namespace: str, release_name: str, ctx) -> dict:
    """Get status of a Helm release (chart version, deployed revision, status)."""
```

---

## PostgreSQL MCP Server — Tool Catalog

```python
@server.mcp.tool("create_database")
async def create_database(cluster: str, db_name: str, owner: str, ctx) -> dict:
    """Create a new database on the specified Postgres cluster."""

@server.mcp.tool("apply_migration")
async def apply_migration(connection_string_vault_path: str, migration_script: str, ctx) -> dict:
    """Apply a SQL migration script to the specified database."""

@server.mcp.tool("run_schema_diff")
async def run_schema_diff(source_conn: str, target_conn: str, ctx) -> dict:
    """Compare schemas between two databases and return differences."""

@server.mcp.tool("generate_seed_script")
async def generate_seed_script(schema: dict, entity_count: int, ctx) -> str:
    """Generate realistic seed data SQL for the specified schema."""

@server.mcp.tool("get_connection_string_template")
async def get_connection_string_template(environment: str, db_name: str, ctx) -> str:
    """Get the connection string template (with Vault path placeholder) for an environment."""

@server.mcp.tool("run_health_check")
async def run_health_check(cluster: str, ctx) -> dict:
    """Run a connectivity + performance health check on a Postgres cluster."""
```

---

## Jira MCP Server — Tool Catalog

```python
@server.mcp.tool("create_epic")
async def create_epic(project_key: str, summary: str, description: str,
                      brd_reference: str, ctx) -> dict:
    """Create a Jira epic linked to a BRD reference."""

@server.mcp.tool("create_story")
async def create_story(project_key: str, epic_id: str, story: dict, ctx) -> dict:
    """Create a user story with acceptance criteria (Gherkin format)."""

@server.mcp.tool("transition_ticket")
async def transition_ticket(ticket_id: str, target_status: str, ctx) -> dict:
    """Transition a ticket to a new status (In Progress, In Review, Done)."""

@server.mcp.tool("link_commits")
async def link_commits(ticket_id: str, commit_shas: list[str], ctx) -> dict:
    """Link commit SHAs to a Jira ticket."""

@server.mcp.tool("get_ticket")
async def get_ticket(ticket_id: str, ctx) -> dict:
    """Get ticket details including description, status, acceptance criteria."""

@server.mcp.tool("add_comment")
async def add_comment(ticket_id: str, comment: str, ctx) -> dict:
    """Add a comment to a Jira ticket."""

@server.mcp.tool("search_tickets")
async def search_tickets(jql: str, ctx) -> list[dict]:
    """Search tickets using JQL."""
```

---

## SonarQube MCP Server — Tool Catalog

```python
@server.mcp.tool("get_quality_gate_status")
async def get_quality_gate_status(project_key: str, ctx) -> dict:
    """Get current quality gate status for a project."""

@server.mcp.tool("trigger_analysis")
async def trigger_analysis(project_key: str, branch: str, ctx) -> dict:
    """Trigger a SonarQube analysis for a branch."""

@server.mcp.tool("get_issues")
async def get_issues(project_key: str, severity: str | None,
                     types: list[str] | None, ctx) -> list[dict]:
    """Get SonarQube issues, filtered by severity or type."""

@server.mcp.tool("get_coverage_report")
async def get_coverage_report(project_key: str, ctx) -> dict:
    """Get code coverage metrics for a project."""

@server.mcp.tool("get_technical_debt")
async def get_technical_debt(project_key: str, ctx) -> dict:
    """Get technical debt metrics and top debt-contributing components."""
```

---

## Postman/Newman MCP Server — Tool Catalog

```python
@server.mcp.tool("generate_collection")
async def generate_collection(project_id: str, openapi_spec_url: str,
                               environments: list[str], ctx) -> dict:
    """Generate a Postman collection from an OpenAPI spec with AD Ports standards."""

@server.mcp.tool("run_collection")
async def run_collection(collection_id: str, environment: str,
                         base_url: str, ctx) -> dict:
    """Run a Postman collection against a specified environment via Newman."""

@server.mcp.tool("get_run_report")
async def get_run_report(run_id: str, ctx) -> dict:
    """Get the results of a Newman collection run."""

@server.mcp.tool("get_environment_matrix")
async def get_environment_matrix(collection_id: str, ctx) -> dict:
    """Get the pass/fail matrix across all environments for a collection."""

@server.mcp.tool("update_collection_for_new_endpoint")
async def update_collection(collection_id: str, new_endpoint_spec: dict, ctx) -> dict:
    """Incrementally add a new endpoint to an existing collection."""

@server.mcp.tool("export_collection")
async def export_collection(collection_id: str, format: str, ctx) -> str:
    """Export collection in Postman v2.1 or Bruno format."""
```

---

## Draw.io MCP Server — Tool Catalog

```python
@server.mcp.tool("generate_architecture_diagram")
async def generate_architecture_diagram(components: list[dict],
                                         relationships: list[dict],
                                         diagram_type: str, ctx) -> str:
    """Generate a draw.io diagram XML from a component and relationship list."""

@server.mcp.tool("generate_sequence_diagram")
async def generate_sequence_diagram(actors: list[str],
                                     interactions: list[dict], ctx) -> str:
    """Generate an interaction/sequence diagram."""

@server.mcp.tool("export_diagram_image")
async def export_diagram_image(diagram_xml: str, format: str = "png", ctx) -> bytes:
    """Export a draw.io diagram to PNG or SVG."""

@server.mcp.tool("fetch_adports_stencils")
async def fetch_adports_stencils(ctx) -> list[dict]:
    """Get the AD Ports custom shape/stencil library for draw.io."""
```

---

## Extended CLI Commands

```bash
# AKS
adports-ai aks namespaces --cluster=jul
adports-ai aks logs --namespace=dgd --pod=declaration-service-xxx
adports-ai aks helm-status --namespace=dgd --release=declaration-service

# Database
adports-ai db create --cluster=main --name=dgd_service
adports-ai db diff --source=dev --target=staging --project=dgd

# Project management
adports-ai ticket create --project=JUL --epic=DGD-001 --story "As a cargo operator..."
adports-ai ticket implement JUL-1234

# Security
adports-ai security scan --project=jul-dgd --branch=feature/new-endpoint
adports-ai security issues --project=jul-dgd --severity=HIGH

# Testing
adports-ai test generate --scope=declaration-service --openapi=./openapi.yaml
adports-ai test run --collection=dgd-integration --env=staging
adports-ai test matrix --collection=dgd-integration
```

---

## Step-by-Step Execution Plan

### Week 1 (Parallel — 3 engineers)

**Engineer 1:** AKS MCP + Vault MCP  
**Engineer 2:** PostgreSQL MCP + Draw.io MCP  
**Engineer 3:** SonarQube MCP + Checkmarx MCP

### Week 2 (Parallel)

**Engineer 1:** Jira MCP + Azure Boards MCP  
**Engineer 2:** Postman/Newman MCP  
**Engineer 3:** CLI extensions for all new servers

### Week 3

- [ ] Integration testing across all 9 new servers.
- [ ] Register all servers in MCP Registry.
- [ ] Update IDE connection guide with all new servers.
- [ ] Wire all server health endpoints to Health Monitor stubs.
- [ ] Deploy all servers to AKS.
- [ ] Final test: full developer workflow using only `@adports-*` MCP handles from Cursor.

---

## Gate Criterion

- All 9 MCP servers deployed and registered in MCP Registry.
- All tools in each server respond correctly (automated integration test per server).
- CLI extensions work for all new domains.
- IDE connection guide covers all 12 servers.
- A developer can create a GitLab project, add a Keycloak client, create Jira stories, and run a SonarQube scan using only `adports-ai` CLI commands.

---

*Phase 09 — Additional MCP Servers — AI Portal — v1.0*
