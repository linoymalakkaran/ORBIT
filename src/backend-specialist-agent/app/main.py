"""Backend Specialist Agent — generates production-ready .NET 9 CQRS microservices."""
from __future__ import annotations

import json
import logging
import textwrap
from typing import Annotated, TypedDict
import operator

import httpx
import litellm
from fastapi import FastAPI, HTTPException
from langgraph.graph import END, StateGraph
from opentelemetry.instrumentation.fastapi import FastAPIInstrumentor
from pydantic import BaseModel
from pydantic_settings import BaseSettings, SettingsConfigDict

logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO)


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_prefix="BACKEND_", env_file=".env", extra="ignore")
    litellm_api_base: str = "http://litellm-gateway.litellm.svc:4000"
    litellm_api_key: str = "changeme"
    default_model: str = "gpt-4o"
    ledger_url: str = "http://pipeline-ledger.ai-portal.svc:80"
    gitlab_mcp_url: str = "http://mcp-registry.ai-portal.svc:80"


settings = Settings()
litellm.api_base = settings.litellm_api_base
litellm.api_key = settings.litellm_api_key

# ── LangGraph State ──────────────────────────────────────────────────────────

class BackendGenState(TypedDict):
    project_id: str
    service_name: str
    responsibility: str
    openapi_stub: str
    domain_entities: Annotated[list[str], operator.add]
    cqrs_handlers: Annotated[list[str], operator.add]
    ef_context: str
    program_cs: str
    dockerfile: str
    helm_values: str
    unit_tests: Annotated[list[str], operator.add]


# ── LLM helper ───────────────────────────────────────────────────────────────

async def _llm(prompt: str, system: str = "You are a senior .NET 9 architect.") -> str:
    r = await litellm.acompletion(
        model=settings.default_model,
        messages=[{"role": "system", "content": system}, {"role": "user", "content": prompt}],
        temperature=0.05,
    )
    return r.choices[0].message.content or ""


# ── Graph Nodes ───────────────────────────────────────────────────────────────

async def generate_domain_entities(state: BackendGenState) -> dict:
    prompt = f"""Generate .NET 9 C# domain entities for a '{state['service_name']}' service.
Responsibility: {state['responsibility']}
OpenAPI spec excerpt: {state['openapi_stub'][:1500]}

Requirements:
- Use record types where immutable, classes where mutable
- Include IDs as Guid
- Follow DDD — rich domain model with private setters
- Add EF Core value objects where appropriate
- Use AdPorts convention: namespace {state['service_name']}.Domain.Entities

Output ONLY C# code. No explanation."""
    code = await _llm(prompt)
    return {"domain_entities": [code]}


async def generate_cqrs_handlers(state: BackendGenState) -> dict:
    prompt = f"""Generate .NET 9 MediatR CQRS command/query handlers for '{state['service_name']}'.
Domain entities: {state['domain_entities'][0][:1000] if state['domain_entities'] else 'not yet generated'}
OpenAPI spec: {state['openapi_stub'][:1500]}

Generate:
1. CreateCommand + CreateCommandHandler
2. GetByIdQuery + GetByIdQueryHandler
3. ListQuery + ListQueryHandler
4. UpdateCommand + UpdateCommandHandler

Use:
- FluentValidation for command validators
- MediatR IPipelineBehavior for validation
- IRepository pattern
- IUnitOfWork
- namespace {state['service_name']}.Application.{state['service_name']}s

Output ONLY C# code."""
    code = await _llm(prompt)
    return {"cqrs_handlers": [code]}


async def generate_ef_context(state: BackendGenState) -> dict:
    prompt = f"""Generate EF Core 9 DbContext + initial migration for '{state['service_name']}':

Domain entities:
{state['domain_entities'][0][:800] if state['domain_entities'] else ''}

Requirements:
- Inherit from DbContext
- Use Npgsql provider (CloudNativePG)
- Configure using IEntityTypeConfiguration<T> classes
- Add audit fields (CreatedAt, UpdatedAt) via SaveChangesAsync override
- namespace {state['service_name']}.Infrastructure.Persistence

Output ONLY C# code."""
    code = await _llm(prompt)
    return {"ef_context": code}


async def generate_program_cs(state: BackendGenState) -> dict:
    prompt = f"""Generate a complete Program.cs for a .NET 9 microservice named '{state['service_name']}'.

Include:
- Serilog structured logging → OTEL collector at otel-collector.monitoring.svc:4317
- OpenTelemetry tracing + metrics (OTLP gRPC exporter)
- MediatR + FluentValidation
- EF Core with Npgsql
- Keycloak JWT bearer auth (authority=https://auth.ai.adports.ae/realms/ai-portal)
- Health checks: /health/live and /health/ready (with EF Core + Redis checks)
- Swagger/OpenAPI with JWT auth
- CORS for portal-ui
- Kong upstream headers
- Vault Agent: reads secrets from /vault/secrets/

Output ONLY C# code for Program.cs."""
    code = await _llm(prompt)
    return {"program_cs": code}


async def generate_dockerfile(state: BackendGenState) -> dict:
    svc_lower = state['service_name'].lower()
    dockerfile = textwrap.dedent(f"""\
        FROM harbor.ai.adports.ae/orbit/dotnet-sdk:9.0 AS build
        WORKDIR /src
        COPY src/{state['service_name']}/{state['service_name']}.csproj .
        RUN dotnet restore
        COPY src/{state['service_name']}/ .
        RUN dotnet publish -c Release -o /app/publish --no-restore

        FROM harbor.ai.adports.ae/orbit/dotnet-runtime:9.0 AS runtime
        WORKDIR /app
        COPY --from=build /app/publish .
        ENV ASPNETCORE_URLS=http://+:8080
        EXPOSE 8080
        ENTRYPOINT ["dotnet", "{state['service_name']}.dll"]
    """)
    return {"dockerfile": dockerfile}


async def generate_helm_values(state: BackendGenState) -> dict:
    svc_lower = state['service_name'].lower()
    values = textwrap.dedent(f"""\
        replicaCount: 2

        image:
          repository: harbor.ai.adports.ae/orbit/{svc_lower}
          tag: latest
          pullPolicy: IfNotPresent

        imagePullSecrets:
          - name: harbor-pull-secret

        service:
          type: ClusterIP
          port: 80
          targetPort: 8080

        ingress:
          enabled: true
          className: kong
          host: {svc_lower}.ai.adports.ae
          tls:
            secretName: {svc_lower}-tls
            clusterIssuer: adports-internal-ca

        vault:
          role: {svc_lower}
          secretPaths:
            - secret/data/{svc_lower}/db
            - secret/data/{svc_lower}/keycloak

        resources:
          requests:
            cpu: 250m
            memory: 512Mi
          limits:
            cpu: 1000m
            memory: 1Gi

        readinessProbe:
          path: /health/ready
          initialDelaySeconds: 15
        livenessProbe:
          path: /health/live
          initialDelaySeconds: 20
    """)
    return {"helm_values": values}


async def generate_unit_tests(state: BackendGenState) -> dict:
    prompt = f"""Generate xUnit + Testcontainers unit/integration tests for '{state['service_name']}' handlers.

Test the CQRS handlers. Use:
- xUnit with FluentAssertions
- Testcontainers for PostgreSQL
- Moq for dependencies
- Test naming: MethodName_StateUnderTest_ExpectedBehavior

Generate at least 3 test classes covering Create, GetById, and List scenarios.
namespace {state['service_name']}.Tests

Output ONLY C# code."""
    code = await _llm(prompt)
    return {"unit_tests": [code]}


def _build_graph():
    g = StateGraph(BackendGenState)
    for name, fn in [
        ("generate_domain_entities", generate_domain_entities),
        ("generate_cqrs_handlers", generate_cqrs_handlers),
        ("generate_ef_context", generate_ef_context),
        ("generate_program_cs", generate_program_cs),
        ("generate_dockerfile", generate_dockerfile),
        ("generate_helm_values", generate_helm_values),
        ("generate_unit_tests", generate_unit_tests),
    ]:
        g.add_node(name, fn)
    g.add_edge("generate_domain_entities", "generate_cqrs_handlers")
    g.add_edge("generate_cqrs_handlers", "generate_ef_context")
    g.add_edge("generate_ef_context", "generate_program_cs")
    g.add_edge("generate_program_cs", "generate_dockerfile")
    g.add_edge("generate_dockerfile", "generate_helm_values")
    g.add_edge("generate_helm_values", "generate_unit_tests")
    g.add_edge("generate_unit_tests", END)
    g.set_entry_point("generate_domain_entities")
    return g.compile()


_graph = _build_graph()

# ── FastAPI ──────────────────────────────────────────────────────────────────

app = FastAPI(title="ORBIT Backend Specialist Agent", version="1.0.0")
FastAPIInstrumentor.instrument_app(app)


class BackendGenRequest(BaseModel):
    project_id: str
    service_name: str
    responsibility: str
    openapi_stub: str = ""


@app.post("/api/generate/backend")
async def generate_backend_service(req: BackendGenRequest):
    """Generate a complete .NET 9 CQRS microservice scaffold."""
    initial: BackendGenState = {
        "project_id": req.project_id,
        "service_name": req.service_name,
        "responsibility": req.responsibility,
        "openapi_stub": req.openapi_stub,
        "domain_entities": [],
        "cqrs_handlers": [],
        "ef_context": "",
        "program_cs": "",
        "dockerfile": "",
        "helm_values": "",
        "unit_tests": [],
    }
    result = await _graph.ainvoke(initial)
    # Ledger record
    try:
        async with httpx.AsyncClient(timeout=5) as client:
            await client.post(f"{settings.ledger_url}/api/ledger", json={
                "project_id": req.project_id,
                "pipeline_run_id": f"backend-gen-{req.service_name}",
                "stage": "backend_generation",
                "actor": "backend-specialist-agent",
                "status": "success",
                "metadata": {"service_name": req.service_name},
            })
    except Exception:
        pass
    return {
        "project_id": result["project_id"],
        "service_name": result["service_name"],
        "artifacts": {
            "domain_entities": result["domain_entities"],
            "cqrs_handlers": result["cqrs_handlers"],
            "ef_context": result["ef_context"],
            "program_cs": result["program_cs"],
            "dockerfile": result["dockerfile"],
            "helm_values": result["helm_values"],
            "unit_tests": result["unit_tests"],
        },
    }


@app.get("/health/live")
async def liveness():
    return {"status": "ok"}


@app.get("/health/ready")
async def readiness():
    return {"status": "ok"}
