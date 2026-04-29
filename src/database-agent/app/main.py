"""Database Agent — PostgreSQL migration generation, RLS policies, index recommendations."""
from __future__ import annotations

import logging
from typing import Annotated, TypedDict
import operator

import httpx
import litellm
from fastapi import FastAPI
from langgraph.graph import END, StateGraph
from opentelemetry.instrumentation.fastapi import FastAPIInstrumentor
from pydantic import BaseModel
from pydantic_settings import BaseSettings, SettingsConfigDict

logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO)


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_prefix="DBAGENT_", env_file=".env", extra="ignore")
    litellm_api_base: str = "http://litellm-gateway.litellm.svc:4000"
    litellm_api_key: str = "changeme"
    default_model: str = "gpt-4o"
    ledger_url: str = "http://pipeline-ledger.ai-portal.svc:80"


settings = Settings()
litellm.api_base = settings.litellm_api_base
litellm.api_key = settings.litellm_api_key


class DbGenState(TypedDict):
    project_id: str
    service_name: str
    domain_entities: str
    openfga_model: str
    migrations: Annotated[list[str], operator.add]
    rls_policies: Annotated[list[str], operator.add]
    index_recommendations: Annotated[list[str], operator.add]
    seed_scripts: Annotated[list[str], operator.add]


async def _llm(prompt: str, system: str = "You are a senior PostgreSQL DBA and .NET architect.") -> str:
    r = await litellm.acompletion(
        model=settings.default_model,
        messages=[{"role": "system", "content": system}, {"role": "user", "content": prompt}],
        temperature=0.05,
    )
    return r.choices[0].message.content or ""


async def generate_migrations(state: DbGenState) -> dict:
    prompt = f"""Generate EF Core 9 + DbUp SQL migration for service '{state['service_name']}'.

Domain entities:
{state['domain_entities'][:2000]}

Requirements:
- EF Core migration class (MigrationName: 'InitialCreate')
- Raw SQL equivalent (DbUp script)
- Include: audit columns (created_at, updated_at, created_by), soft delete (deleted_at)
- Use snake_case for PostgreSQL column/table names
- Schema: {state['service_name'].lower()}

Output ONLY SQL migration followed by EF Core Up() / Down() C# code."""
    sql = await _llm(prompt)
    return {"migrations": [sql]}


async def generate_rls_policies(state: DbGenState) -> dict:
    prompt = f"""Generate PostgreSQL Row Level Security policies for '{state['service_name']}'.

OpenFGA model context:
{state['openfga_model'][:1000] if state['openfga_model'] else 'Standard RBAC: admin, editor, viewer roles'}

Requirements:
- Enable RLS on all tables
- Policies per role: admin (all), editor (own + shared), viewer (shared only)
- Use current_setting('app.current_user_id') for user context
- Use current_setting('app.current_role') for role context
- Include GRANT statements

Output ONLY SQL (PostgreSQL)."""
    sql = await _llm(prompt)
    return {"rls_policies": [sql]}


async def generate_index_recommendations(state: DbGenState) -> dict:
    prompt = f"""Generate PostgreSQL index recommendations for '{state['service_name']}' based on:

Domain entities:
{state['domain_entities'][:1500]}

Include:
- B-tree indexes on foreign keys and commonly filtered columns
- GIN indexes for full-text search columns
- Partial indexes for soft-deleted rows
- Composite indexes for common query patterns
- EXPLAIN ANALYZE rationale for each index

Output ONLY SQL CREATE INDEX statements with comments."""
    sql = await _llm(prompt)
    return {"index_recommendations": [sql]}


async def generate_seed_scripts(state: DbGenState) -> dict:
    prompt = f"""Generate development seed data SQL scripts for '{state['service_name']}'.

Domain entities:
{state['domain_entities'][:1000]}

Requirements:
- 10-20 realistic dev records per main entity
- Reference data (lookups, enums)
- Use ON CONFLICT DO NOTHING for idempotency
- Include a script header comment with execution order

Output ONLY SQL."""
    sql = await _llm(prompt)
    return {"seed_scripts": [sql]}


def _build_graph():
    g = StateGraph(DbGenState)
    for name, fn in [
        ("generate_migrations", generate_migrations),
        ("generate_rls_policies", generate_rls_policies),
        ("generate_index_recommendations", generate_index_recommendations),
        ("generate_seed_scripts", generate_seed_scripts),
    ]:
        g.add_node(name, fn)
    g.add_edge("generate_migrations", "generate_rls_policies")
    g.add_edge("generate_rls_policies", "generate_index_recommendations")
    g.add_edge("generate_index_recommendations", "generate_seed_scripts")
    g.add_edge("generate_seed_scripts", END)
    g.set_entry_point("generate_migrations")
    return g.compile()


_db_graph = _build_graph()

app = FastAPI(title="ORBIT Database & Integration Agents", version="1.0.0")
FastAPIInstrumentor.instrument_app(app)


class DbGenRequest(BaseModel):
    project_id: str
    service_name: str
    domain_entities: str
    openfga_model: str = ""


@app.post("/api/generate/database")
async def generate_database(req: DbGenRequest):
    """Generate PostgreSQL migrations, RLS policies, indexes, and seed data."""
    initial: DbGenState = {
        "project_id": req.project_id,
        "service_name": req.service_name,
        "domain_entities": req.domain_entities,
        "openfga_model": req.openfga_model,
        "migrations": [],
        "rls_policies": [],
        "index_recommendations": [],
        "seed_scripts": [],
    }
    result = await _db_graph.ainvoke(initial)
    try:
        async with httpx.AsyncClient(timeout=5) as client:
            await client.post(f"{settings.ledger_url}/api/ledger", json={
                "project_id": req.project_id,
                "pipeline_run_id": f"db-gen-{req.service_name}",
                "stage": "database_generation",
                "actor": "database-agent",
                "status": "success",
                "metadata": {"service_name": req.service_name},
            })
    except Exception:
        pass
    return {
        "project_id": result["project_id"],
        "service_name": result["service_name"],
        "artifacts": {
            "migrations": result["migrations"],
            "rls_policies": result["rls_policies"],
            "index_recommendations": result["index_recommendations"],
            "seed_scripts": result["seed_scripts"],
        },
    }


# ── Integration Agent endpoints ───────────────────────────────────────────────

class IntegrationGenRequest(BaseModel):
    project_id: str
    service_name: str
    events: list[str]           # event names to generate consumers for
    sagas: list[str] = []       # saga names


@app.post("/api/generate/integration")
async def generate_integration(req: IntegrationGenRequest):
    """Generate MassTransit consumers, Saga state machines, inbox/outbox pattern."""
    events_list = "\n".join(f"- {e}" for e in req.events)
    sagas_list = "\n".join(f"- {s}" for s in req.sagas)

    consumers_prompt = f"""Generate .NET 9 MassTransit consumer classes for service '{req.service_name}'.

Events to consume:
{events_list}

Requirements:
- IConsumer<T> implementation per event
- Use Kafka transport (MassTransit.KafkaRider)
- Include DI registration in extension method
- Add retry policy (3 retries, exponential backoff)
- Log using Serilog with correlation ID
- namespace {req.service_name}.Infrastructure.Messaging

Output ONLY C# code."""

    saga_prompt = f"""Generate MassTransit Saga state machine definitions for '{req.service_name}'.

Sagas to implement:
{sagas_list if sagas_list else 'OrderProcessingSaga'}

Requirements:
- Use MassTransitStateMachine<TState>
- Persistent saga state (PostgreSQL with EF Core)
- Include all State / Event / Behavior definitions
- Add compensating transactions for failure paths
- namespace {req.service_name}.Application.Sagas

Output ONLY C# code."""

    outbox_prompt = f"""Generate .NET 9 Transactional Outbox pattern for '{req.service_name}'.

Requirements:
- OutboxMessage entity + EF Core config
- OutboxPublisher (writes to outbox within same EF transaction)
- OutboxWorker (BackgroundService that polls and publishes)
- Use MassTransit outbox integration
- namespace {req.service_name}.Infrastructure.Outbox

Output ONLY C# code."""

    consumers, saga_code, outbox_code = await asyncio.gather(
        _llm(consumers_prompt),
        _llm(saga_prompt),
        _llm(outbox_prompt),
    )

    try:
        async with httpx.AsyncClient(timeout=5) as client:
            await client.post(f"{settings.ledger_url}/api/ledger", json={
                "project_id": req.project_id,
                "pipeline_run_id": f"integration-gen-{req.service_name}",
                "stage": "integration_generation",
                "actor": "integration-agent",
                "status": "success",
                "metadata": {"service_name": req.service_name, "events": req.events},
            })
    except Exception:
        pass

    return {
        "project_id": req.project_id,
        "service_name": req.service_name,
        "artifacts": {
            "consumers": consumers,
            "saga_state_machines": saga_code,
            "outbox_pattern": outbox_code,
        },
    }


@app.get("/health/live")
async def liveness():
    return {"status": "ok"}


@app.get("/health/ready")
async def readiness():
    return {"status": "ok"}


# ── G13: Camunda BPMN Generator ──────────────────────────────────────────────

import textwrap as _textwrap


class BpmnStep(BaseModel):
    name: str
    type: str  # "user_task" | "service_task" | "exclusive_gateway" | "parallel_gateway" | "send_task"
    assignee: str | None = None
    form_key: str | None = None
    description: str = ""


class WorkflowGenRequest(BaseModel):
    project_id: str
    process_name: str
    process_id: str = ""   # auto-derived from process_name if empty
    steps: list[BpmnStep]
    variables: list[str] = []


@app.post("/api/generate/workflow")
async def generate_workflow(req: WorkflowGenRequest):
    """
    Phase 14 – G13: Generates a valid Camunda 8 BPMN 2.0 XML process definition
    and a deployment curl command for Zeebe.
    """
    process_id = req.process_id or req.process_name.lower().replace(" ", "-")
    steps_text = "\n".join(
        f"  {i+1}. type={s.type} name={s.name} assignee={s.assignee} form={s.form_key}"
        for i, s in enumerate(req.steps)
    )
    variables_text = ", ".join(req.variables) or "none"

    prompt = _textwrap.dedent(f"""
        Generate a valid Camunda 8 BPMN 2.0 XML file for this process.

        Process name: {req.process_name}
        Process ID: {process_id}
        Process variables: {variables_text}

        Steps (in order):
        {steps_text}

        Requirements:
        - Use namespace: xmlns:bpmn="http://www.omg.org/spec/BPMN/20100524/MODEL"
        - Add xmlns:zeebe="http://camunda.org/schema/zeebe/1.0" for Camunda 8 extensions
        - Add xmlns:modeler="http://camunda.org/schema/modeler/1.0"
        - Include startEvent, endEvent, all steps as correct BPMN element types
        - For user_task: add zeebe:assignmentDefinition assignee attribute
        - For service_task: add zeebe:taskDefinition type attribute (use process_id + "_" + step_name)
        - For exclusive_gateway: add sequenceFlows with conditionExpression
        - For parallel_gateway: add parallel split + join pair
        - Add bpmndi:BPMNDiagram section with layout coordinates
        - Sequence flows connect all elements in order
        Return ONLY the complete XML starting with <?xml version="1.0" encoding="UTF-8"?>
    """)

    bpmn_xml = await _llm(prompt)

    # Generate Zeebe deployment command
    deploy_cmd = (
        f'curl -X POST http://zeebe.camunda.svc:26500/api/v1/deployments \\\n'
        f'  -H "Content-Type: multipart/form-data" \\\n'
        f'  -F "resources=@{process_id}.bpmn;type=application/xml"'
    )

    # Record in ledger
    try:
        async with httpx.AsyncClient(timeout=5) as client:
            await client.post(f"{settings.ledger_url}/api/ledger", json={
                "project_id": req.project_id,
                "pipeline_run_id": f"workflow-gen-{process_id}",
                "stage": "workflow_generation",
                "actor": "database-agent",
                "status": "success",
                "metadata": {"process_id": process_id, "steps": len(req.steps)},
            })
    except Exception:
        pass

    return {
        "project_id": req.project_id,
        "process_id": process_id,
        "process_name": req.process_name,
        "artifacts": {
            "bpmn_xml": bpmn_xml,
            "deploy_command": deploy_cmd,
            "filename": f"{process_id}.bpmn",
        },
    }


import asyncio
