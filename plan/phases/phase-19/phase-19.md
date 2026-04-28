# Phase 19 — Project Registry

## Summary

Implement the **Project Registry** — the central catalog of all AI-assisted projects, their lifecycle status, ownership, linked repositories, deployed environments, and health indicators. The Registry is the single source of truth for "what exists" in the AD Ports software landscape and powers the Fleet Upgrade agent (Phase 24), the Service Health Monitor (Phase 20), and the BA/PM agent (Phase 22).

---

## Objectives

1. Implement Project Registry data model (project, service, environment, framework version).
2. Implement project registration flow (auto-register when project is approved).
3. Implement service inventory (all microservices + frameworks + versions from AKS).
4. Implement framework version tracking (Angular, .NET, Node.js per service).
5. Implement lifecycle state machine (Draft → Active → Deprecated → Retired).
6. Implement dependency graph (which services depend on which).
7. Implement Registry REST API (CRUD + search + graph query).
8. Implement Registry UI (project list, service map, dependency graph, health overview).
9. Implement AKS sync job (pulls running service versions from AKS cluster).
10. Implement Registry MCP server (exposes Registry to Orchestrator and agents).

---

## Prerequisites

- Phase 02 (Core Data Layer — projects table is the foundation).
- Phase 01 (AKS — where services are running).
- Phase 09 (AKS MCP — to pull workload info).
- Phase 10 (Orchestrator — Registry tools used by all agents).

---

## Duration

**3 weeks** (runs in parallel with Phases 16–17)

**Squad:** Platform Squad (1 senior .NET + 1 Angular + 1 Python/AI)

---

## Deliverables

| # | Deliverable | Acceptance Criterion |
|---|------------|---------------------|
| D1 | Project Registry DB schema | Schema migrated; DGD project + 3 services registered |
| D2 | Auto-registration flow | Approval of architecture proposal auto-creates Registry entry |
| D3 | Service inventory | AKS sync job pulls all workloads with framework versions |
| D4 | Framework version tracking | Angular/dotnet/node version per service stored and queryable |
| D5 | Lifecycle state machine | DGD project transitions Draft → Active correctly |
| D6 | Dependency graph | Services with their upstreams/downstreams queryable as graph |
| D7 | Registry API | All CRUD + search endpoints working; OpenAPI spec published |
| D8 | Registry UI | Project list + service map + dependency graph render correctly |
| D9 | AKS sync job | Scheduled sync every 15 min; drift detected and alerted |
| D10 | Registry MCP server | 5 MCP tools callable from Orchestrator agents |

---

## Data Model

```sql
-- Project Registry schema
CREATE SCHEMA registry;

CREATE TABLE registry.projects (
    id              uuid        PRIMARY KEY DEFAULT gen_random_uuid(),
    name            text        NOT NULL,
    description     text,
    business_domain text        NOT NULL,  -- e.g. 'DGD', 'JUL', 'PCS'
    status          text        NOT NULL DEFAULT 'draft',  -- draft/active/deprecated/retired
    owner_team      text        NOT NULL,
    gitlab_group    text,
    created_at      timestamptz NOT NULL DEFAULT now(),
    created_by      uuid        REFERENCES portal.users(id)
);

CREATE TABLE registry.services (
    id              uuid        PRIMARY KEY DEFAULT gen_random_uuid(),
    project_id      uuid        NOT NULL REFERENCES registry.projects(id),
    name            text        NOT NULL,
    service_type    text        NOT NULL,  -- backend/frontend/mfe/worker/bff
    programming_language text   NOT NULL,  -- csharp/typescript/python
    framework       text        NOT NULL,  -- dotnet/angular/fastapi
    framework_version text      NOT NULL,
    gitlab_repo_url text,
    helm_chart_path text,
    aks_namespace   text,
    aks_deployment  text,
    last_synced_at  timestamptz,
    health_status   text        NOT NULL DEFAULT 'unknown'
);

CREATE TABLE registry.service_dependencies (
    id              uuid        PRIMARY KEY DEFAULT gen_random_uuid(),
    from_service_id uuid        NOT NULL REFERENCES registry.services(id),
    to_service_id   uuid        NOT NULL REFERENCES registry.services(id),
    dependency_type text        NOT NULL,  -- http/messaging/database/mfe-remote
    UNIQUE (from_service_id, to_service_id, dependency_type)
);

CREATE TABLE registry.environments (
    id              uuid        PRIMARY KEY DEFAULT gen_random_uuid(),
    service_id      uuid        NOT NULL REFERENCES registry.services(id),
    environment     text        NOT NULL,  -- dev/staging/production
    aks_namespace   text        NOT NULL,
    image_tag       text,
    deployed_at     timestamptz,
    deployed_by     text,
    health_url      text,
    last_health_check_at timestamptz,
    health_status   text        DEFAULT 'unknown'
);

CREATE INDEX idx_services_framework ON registry.services (framework, framework_version);
CREATE INDEX idx_services_project ON registry.services (project_id);
```

---

## AKS Sync Job

```python
# registry_sync/aks_sync.py
async def sync_from_aks() -> SyncResult:
    """Pull workload info from AKS and update Registry."""
    workloads = await aks_mcp.list_deployments(namespace="*")

    updated = 0
    for workload in workloads:
        # Parse image tag to extract service info
        image = workload.containers[0].image
        service_name, version = parse_image(image)

        # Lookup Registry entry
        service = await registry_db.find_service_by_aks_deployment(
            namespace=workload.namespace,
            deployment=workload.name
        )

        if service:
            # Update version + health
            await registry_db.update_service(service.id, {
                "framework_version": extract_framework_version(image),
                "last_synced_at": datetime.utcnow(),
                "health_status": workload.status  # Running/Pending/Failed
            })
            updated += 1
        else:
            # Drift detected — AKS has a workload not in Registry
            await alerts.send(
                f"Unregistered service detected in AKS: {workload.namespace}/{workload.name}"
            )

    return SyncResult(total=len(workloads), updated=updated)
```

---

## Registry MCP Server

The Registry exposes 5 MCP tools used by other agents:

```python
# MCP tools available to Orchestrator agents

@mcp_tool("registry.find_project")
async def find_project(name: str | None = None, domain: str | None = None) -> list[Project]:
    """Find projects by name or business domain."""

@mcp_tool("registry.get_service_inventory")
async def get_service_inventory(project_id: str) -> list[Service]:
    """Get all services for a project with their framework versions."""

@mcp_tool("registry.get_dependency_graph")
async def get_dependency_graph(service_id: str, depth: int = 2) -> DependencyGraph:
    """Get upstream and downstream dependencies for a service."""

@mcp_tool("registry.register_service")
async def register_service(service: ServiceRegistration) -> Service:
    """Register a new service (called by Backend/Frontend Agent after repo creation)."""

@mcp_tool("registry.find_outdated_frameworks")
async def find_outdated_frameworks(framework: str, below_version: str) -> list[Service]:
    """Find all services using a framework version below the specified version."""
```

---

## Registry UI

The Registry UI is a dedicated section in the AD Ports AI Portal:

```html
<!-- registry/registry-dashboard.component.ts -->
<div class="registry-layout">
  <!-- Project catalog -->
  <adports-project-list
    [projects]="projects()"
    [filters]="filters"
    (projectSelected)="onProjectSelected($event)"
  />

  <!-- Service dependency graph (D3.js force-directed) -->
  <adports-dependency-graph
    [services]="selectedProject()?.services"
    [dependencies]="selectedProject()?.dependencies"
  />

  <!-- Health overview table -->
  <adports-health-overview
    [environments]="selectedProject()?.environments"
  />

  <!-- Framework version heatmap -->
  <adports-framework-heatmap
    [services]="services()"
    [latestVersions]="latestFrameworkVersions()"
  />
</div>
```

The framework heatmap shows all services color-coded by how outdated their frameworks are (green = current, yellow = 1 major behind, red = 2+ majors behind).

---

## Step-by-Step Execution Plan

### Week 1: DB + API

- [ ] Design and migrate Project Registry schema.
- [ ] Implement CRUD API (projects, services, dependencies, environments).
- [ ] Implement search endpoint (search by name, domain, framework, status).
- [ ] Implement auto-registration hook (called after architecture approval).
- [ ] Unit tests for all API endpoints.

### Week 2: AKS Sync + Registry MCP

- [ ] Implement AKS sync job (pull workloads, compare, update Registry).
- [ ] Implement drift detection and alerting.
- [ ] Implement Registry MCP server (5 tools).
- [ ] Test: DGD services auto-registered; AKS sync populates versions.

### Week 3: Registry UI

- [ ] Implement project list with search and filter.
- [ ] Implement service dependency graph (D3.js force-directed layout).
- [ ] Implement health overview table.
- [ ] Implement framework version heatmap.
- [ ] End-to-end test: DGD project visible in Registry UI with correct health status.

---

## Gate Criterion (Gate 2 Prerequisite)

- DGD project and all 5 services registered in Registry with correct framework versions.
- AKS sync job runs every 15 minutes; unregistered workloads alert correctly.
- Dependency graph shows DGD service relationships.
- Registry MCP tools callable from Orchestrator (`registry.find_outdated_frameworks` returns correct results).
- Registry UI accessible in Portal at `/registry`.

---

*Phase 19 — Project Registry — AI Portal — v1.0*
