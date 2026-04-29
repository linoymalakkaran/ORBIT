"""Project Registry — central catalog of all AI-assisted projects, services, and environments."""
from __future__ import annotations

import asyncio
import logging
from datetime import datetime, timezone
from enum import Enum
from typing import Optional
from uuid import UUID, uuid4

import asyncpg
import httpx
from fastapi import FastAPI, HTTPException, Query, status
from opentelemetry.instrumentation.fastapi import FastAPIInstrumentor
from pydantic import BaseModel, Field
from pydantic_settings import BaseSettings, SettingsConfigDict

logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO)


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_prefix="REGISTRY_", env_file=".env", extra="ignore")
    db_dsn: str = "postgresql://postgres:changeme@postgresql.ai-portal.svc:5432/orbit"
    kubernetes_mcp_url: str = "http://mcp-registry.ai-portal.svc:80"
    ledger_url: str = "http://pipeline-ledger.ai-portal.svc:80"
    aks_sync_interval_seconds: int = 300


settings = Settings()


# ── Domain Models ─────────────────────────────────────────────────────────────

class LifecycleState(str, Enum):
    DRAFT = "Draft"
    ACTIVE = "Active"
    DEPRECATED = "Deprecated"
    RETIRED = "Retired"


class ProjectRecord(BaseModel):
    id: UUID = Field(default_factory=uuid4)
    name: str
    description: str = ""
    owner_team: str
    project_type: str           # payment | crm | iac | portal | etc.
    lifecycle_state: LifecycleState = LifecycleState.DRAFT
    gitlab_repo_url: Optional[str] = None
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


class ServiceRecord(BaseModel):
    id: UUID = Field(default_factory=uuid4)
    project_id: UUID
    name: str
    service_type: str           # dotnet | python | angular
    framework_name: str         # dotnet | angular | node | python
    framework_version: str      # 9.0 | 20 | 20.x | 3.12
    image: str                  # harbor.ai.adports.ae/orbit/<name>:<tag>
    namespace: str = "ai-portal"
    deployed_envs: list[str] = Field(default_factory=list)   # dev | staging | prod
    depends_on: list[UUID] = Field(default_factory=list)
    last_health_check: Optional[datetime] = None
    health_status: str = "unknown"   # healthy | degraded | unhealthy | unknown
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


class FrameworkVersion(BaseModel):
    framework: str
    current_version: str
    latest_version: str
    versions_behind: int
    is_compliant: bool          # False if >2 major versions behind


# ── Database ──────────────────────────────────────────────────────────────────

_pool: asyncpg.Pool | None = None


async def get_pool() -> asyncpg.Pool:
    global _pool
    if _pool is None:
        _pool = await asyncpg.create_pool(settings.db_dsn, min_size=2, max_size=10)
        await _init_schema()
    return _pool


async def _init_schema():
    pool = await get_pool()
    async with pool.acquire() as conn:
        await conn.execute("""
            CREATE SCHEMA IF NOT EXISTS registry;

            CREATE TABLE IF NOT EXISTS registry.projects (
                id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
                name TEXT NOT NULL,
                description TEXT NOT NULL DEFAULT '',
                owner_team TEXT NOT NULL,
                project_type TEXT NOT NULL,
                lifecycle_state TEXT NOT NULL DEFAULT 'Draft',
                gitlab_repo_url TEXT,
                created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
                updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
            );

            CREATE TABLE IF NOT EXISTS registry.services (
                id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
                project_id UUID NOT NULL REFERENCES registry.projects(id) ON DELETE CASCADE,
                name TEXT NOT NULL,
                service_type TEXT NOT NULL,
                framework_name TEXT NOT NULL,
                framework_version TEXT NOT NULL,
                image TEXT NOT NULL,
                namespace TEXT NOT NULL DEFAULT 'ai-portal',
                deployed_envs TEXT[] NOT NULL DEFAULT '{}',
                depends_on UUID[] NOT NULL DEFAULT '{}',
                last_health_check TIMESTAMPTZ,
                health_status TEXT NOT NULL DEFAULT 'unknown',
                created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
                updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
            );

            CREATE INDEX IF NOT EXISTS idx_services_project_id ON registry.services(project_id);
            CREATE INDEX IF NOT EXISTS idx_projects_lifecycle ON registry.projects(lifecycle_state);
            CREATE INDEX IF NOT EXISTS idx_services_health ON registry.services(health_status);
        """)


# ── FastAPI ──────────────────────────────────────────────────────────────────

app = FastAPI(title="ORBIT Project Registry", version="1.0.0")
FastAPIInstrumentor.instrument_app(app)


@app.on_event("startup")
async def startup():
    await get_pool()


# ── Projects CRUD ─────────────────────────────────────────────────────────────

class CreateProjectRequest(BaseModel):
    name: str
    description: str = ""
    owner_team: str
    project_type: str
    gitlab_repo_url: Optional[str] = None


@app.post("/api/registry/projects", status_code=status.HTTP_201_CREATED)
async def create_project(req: CreateProjectRequest):
    pool = await get_pool()
    async with pool.acquire() as conn:
        row = await conn.fetchrow("""
            INSERT INTO registry.projects (name, description, owner_team, project_type, gitlab_repo_url)
            VALUES ($1, $2, $3, $4, $5)
            RETURNING id, name, description, owner_team, project_type, lifecycle_state, gitlab_repo_url, created_at, updated_at
        """, req.name, req.description, req.owner_team, req.project_type, req.gitlab_repo_url)
    return dict(row)


@app.get("/api/registry/projects")
async def list_projects(
    lifecycle_state: Optional[str] = Query(None),
    project_type: Optional[str] = Query(None),
    owner_team: Optional[str] = Query(None),
    search: Optional[str] = Query(None),
    limit: int = Query(50, le=200),
    offset: int = Query(0),
):
    pool = await get_pool()
    conditions = ["1=1"]
    params: list = []
    i = 1
    if lifecycle_state:
        conditions.append(f"lifecycle_state = ${i}"); params.append(lifecycle_state); i += 1
    if project_type:
        conditions.append(f"project_type = ${i}"); params.append(project_type); i += 1
    if owner_team:
        conditions.append(f"owner_team = ${i}"); params.append(owner_team); i += 1
    if search:
        conditions.append(f"(name ILIKE ${i} OR description ILIKE ${i})"); params.append(f"%{search}%"); i += 1
    where = " AND ".join(conditions)
    async with pool.acquire() as conn:
        rows = await conn.fetch(f"""
            SELECT id, name, description, owner_team, project_type, lifecycle_state,
                   gitlab_repo_url, created_at, updated_at
            FROM registry.projects WHERE {where}
            ORDER BY updated_at DESC LIMIT {limit} OFFSET {offset}
        """, *params)
        total = await conn.fetchval(f"SELECT COUNT(*) FROM registry.projects WHERE {where}", *params)
    return {"items": [dict(r) for r in rows], "total": total, "limit": limit, "offset": offset}


@app.get("/api/registry/projects/{project_id}")
async def get_project(project_id: UUID):
    pool = await get_pool()
    async with pool.acquire() as conn:
        row = await conn.fetchrow("SELECT * FROM registry.projects WHERE id = $1", project_id)
    if not row:
        raise HTTPException(status_code=404, detail="Project not found")
    return dict(row)


@app.patch("/api/registry/projects/{project_id}/lifecycle")
async def transition_lifecycle(project_id: UUID, new_state: LifecycleState):
    pool = await get_pool()
    async with pool.acquire() as conn:
        row = await conn.fetchrow("""
            UPDATE registry.projects SET lifecycle_state = $1, updated_at = NOW()
            WHERE id = $2 RETURNING *
        """, new_state.value, project_id)
    if not row:
        raise HTTPException(status_code=404, detail="Project not found")
    return dict(row)


# ── Services CRUD ─────────────────────────────────────────────────────────────

class RegisterServiceRequest(BaseModel):
    name: str
    service_type: str
    framework_name: str
    framework_version: str
    image: str
    namespace: str = "ai-portal"
    deployed_envs: list[str] = []
    depends_on: list[UUID] = []


@app.post("/api/registry/projects/{project_id}/services", status_code=status.HTTP_201_CREATED)
async def register_service(project_id: UUID, req: RegisterServiceRequest):
    pool = await get_pool()
    async with pool.acquire() as conn:
        project = await conn.fetchrow("SELECT id FROM registry.projects WHERE id = $1", project_id)
        if not project:
            raise HTTPException(status_code=404, detail="Project not found")
        row = await conn.fetchrow("""
            INSERT INTO registry.services
              (project_id, name, service_type, framework_name, framework_version,
               image, namespace, deployed_envs, depends_on)
            VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9)
            RETURNING *
        """, project_id, req.name, req.service_type, req.framework_name,
              req.framework_version, req.image, req.namespace,
              req.deployed_envs, [str(d) for d in req.depends_on])
    return dict(row)


@app.get("/api/registry/projects/{project_id}/services")
async def list_services(project_id: UUID):
    pool = await get_pool()
    async with pool.acquire() as conn:
        rows = await conn.fetch("SELECT * FROM registry.services WHERE project_id = $1 ORDER BY name", project_id)
    return [dict(r) for r in rows]


@app.get("/api/registry/services")
async def list_all_services(
    framework_name: Optional[str] = Query(None),
    health_status: Optional[str] = Query(None),
    namespace: Optional[str] = Query(None),
):
    pool = await get_pool()
    conditions = ["1=1"]
    params: list = []
    i = 1
    if framework_name:
        conditions.append(f"framework_name = ${i}"); params.append(framework_name); i += 1
    if health_status:
        conditions.append(f"health_status = ${i}"); params.append(health_status); i += 1
    if namespace:
        conditions.append(f"namespace = ${i}"); params.append(namespace); i += 1
    where = " AND ".join(conditions)
    async with pool.acquire() as conn:
        rows = await conn.fetch(f"SELECT * FROM registry.services WHERE {where} ORDER BY name", *params)
    return [dict(r) for r in rows]


@app.get("/api/registry/framework-inventory")
async def get_framework_inventory():
    """Returns all unique framework versions across all services with compliance status."""
    pool = await get_pool()
    async with pool.acquire() as conn:
        rows = await conn.fetch("""
            SELECT framework_name, framework_version, COUNT(*) AS service_count
            FROM registry.services
            GROUP BY framework_name, framework_version
            ORDER BY framework_name, framework_version
        """)
    # Latest known versions (static lookup; in production, fetched from GitHub releases)
    latest = {"dotnet": "9.0", "angular": "20", "node": "22", "python": "3.12"}
    inventory = []
    for row in rows:
        fw = row["framework_name"].lower()
        latest_v = latest.get(fw, "unknown")
        try:
            current_major = int(row["framework_version"].split(".")[0])
            latest_major = int(latest_v.split(".")[0])
            versions_behind = latest_major - current_major
        except Exception:
            versions_behind = 0
        inventory.append({
            "framework": row["framework_name"],
            "current_version": row["framework_version"],
            "latest_version": latest_v,
            "service_count": row["service_count"],
            "versions_behind": versions_behind,
            "is_compliant": versions_behind <= 2,
        })
    return inventory


@app.get("/api/registry/dependency-graph")
async def get_dependency_graph(project_id: Optional[UUID] = Query(None)):
    """Returns service dependency graph as nodes + edges."""
    pool = await get_pool()
    async with pool.acquire() as conn:
        if project_id:
            services = await conn.fetch("SELECT id, name, depends_on FROM registry.services WHERE project_id = $1", project_id)
        else:
            services = await conn.fetch("SELECT id, name, depends_on FROM registry.services")
    nodes = [{"id": str(s["id"]), "label": s["name"]} for s in services]
    edges = []
    for s in services:
        for dep in (s["depends_on"] or []):
            edges.append({"from": str(s["id"]), "to": str(dep)})
    return {"nodes": nodes, "edges": edges}


@app.post("/api/registry/sync/kubernetes")
async def sync_from_kubernetes():
    """Trigger a sync of running service versions from Kubernetes via MCP."""
    try:
        async with httpx.AsyncClient(timeout=30) as client:
            resp = await client.post(f"{settings.kubernetes_mcp_url}/invoke/kubernetes-mcp", json={
                "tool": "list_deployments",
                "params": {"namespace": "ai-portal"},
            })
            if resp.status_code != 200:
                raise HTTPException(status_code=resp.status_code, detail="K8s MCP error")
            deployments = resp.json().get("result", {}).get("deployments", [])
    except httpx.RequestError as e:
        raise HTTPException(status_code=503, detail=f"K8s MCP unreachable: {e}")

    updated_count = 0
    pool = await get_pool()
    for dep in deployments:
        name = dep.get("name", "")
        image = dep.get("image", "")
        async with pool.acquire() as conn:
            result = await conn.execute("""
                UPDATE registry.services
                SET image = $1, updated_at = NOW()
                WHERE name = $2
            """, image, name)
            if result != "UPDATE 0":
                updated_count += 1

    return {"synced": len(deployments), "updated": updated_count}


@app.get("/health/live")
async def liveness():
    return {"status": "ok"}


@app.get("/health/ready")
async def readiness():
    try:
        pool = await get_pool()
        async with pool.acquire() as conn:
            await conn.fetchval("SELECT 1")
        db_ok = True
    except Exception:
        db_ok = False
    return {"status": "ok" if db_ok else "degraded", "db": "ok" if db_ok else "error"}
