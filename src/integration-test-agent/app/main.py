"""Integration Test Agent — generates Postman collections from OpenAPI specs and Newman configs."""
from __future__ import annotations

import json
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
    model_config = SettingsConfigDict(env_prefix="ITEST_", env_file=".env", extra="ignore")
    litellm_api_base: str = "http://litellm-gateway.litellm.svc:4000"
    litellm_api_key: str = "changeme"
    default_model: str = "gpt-4o"
    ledger_url: str = "http://pipeline-ledger.ai-portal.svc:80"


settings = Settings()
litellm.api_base = settings.litellm_api_base
litellm.api_key = settings.litellm_api_key


class IntegrationTestState(TypedDict):
    project_id: str
    service_name: str
    openapi_stub: str
    integration_scenarios: list[str]
    postman_collection: str
    environment_dev: str
    environment_staging: str
    environment_prod: str
    newman_config: str
    test_data: str


async def _llm(prompt: str, system: str = "You are a QA engineer expert in Postman and API testing.") -> str:
    r = await litellm.acompletion(
        model=settings.default_model,
        messages=[{"role": "system", "content": system}, {"role": "user", "content": prompt}],
        temperature=0.05,
    )
    return r.choices[0].message.content or ""


async def generate_postman_collection(state: IntegrationTestState) -> dict:
    scenarios = "\n".join(f"- {s}" for s in state["integration_scenarios"])
    prompt = f"""Generate a Postman Collection v2.1 JSON for '{state['service_name']}'.

OpenAPI spec:
{state['openapi_stub'][:2000]}

Integration scenarios:
{scenarios}

Requirements:
- Collection info with proper name and schema v2.1 URL
- Folders per resource/domain
- Pre-request scripts for auth token (Keycloak client credentials)
- Test scripts per request: pm.test() assertions for status code, schema, response time
- Variables: {{{{base_url}}}}, {{{{auth_token}}}}, {{{{tenant_id}}}}
- Chained requests (save response ID to collection variable)

Output ONLY valid Postman Collection v2.1 JSON."""
    collection = await _llm(prompt)
    # Try to parse + reformat; fall back to raw
    try:
        parsed = json.loads(collection)
        collection = json.dumps(parsed, indent=2)
    except Exception:
        pass
    return {"postman_collection": collection}


async def generate_environments(state: IntegrationTestState) -> dict:
    svc_lower = state["service_name"].lower()
    dev_env = json.dumps({
        "id": f"{svc_lower}-dev-env",
        "name": f"{state['service_name']} — Dev",
        "values": [
            {"key": "base_url", "value": f"https://{svc_lower}.ai.adports.ae", "enabled": True},
            {"key": "keycloak_url", "value": "https://auth.ai.adports.ae", "enabled": True},
            {"key": "realm", "value": "ai-portal", "enabled": True},
            {"key": "client_id", "value": f"{svc_lower}-test-client", "enabled": True},
            {"key": "client_secret", "value": "{{REPLACE_FROM_VAULT}}", "enabled": True},
            {"key": "auth_token", "value": "", "enabled": True},
        ],
        "_postman_variable_scope": "environment",
    }, indent=2)
    staging_env = json.dumps({
        "id": f"{svc_lower}-staging-env",
        "name": f"{state['service_name']} — Staging",
        "values": [
            {"key": "base_url", "value": f"https://{svc_lower}-staging.ai.adports.ae", "enabled": True},
            {"key": "keycloak_url", "value": "https://auth.ai.adports.ae", "enabled": True},
            {"key": "realm", "value": "ai-portal", "enabled": True},
            {"key": "client_id", "value": f"{svc_lower}-test-client", "enabled": True},
            {"key": "client_secret", "value": "{{REPLACE_FROM_VAULT}}", "enabled": True},
            {"key": "auth_token", "value": "", "enabled": True},
        ],
        "_postman_variable_scope": "environment",
    }, indent=2)
    prod_env = json.dumps({
        "id": f"{svc_lower}-prod-env",
        "name": f"{state['service_name']} — Prod (Read-Only Tests)",
        "values": [
            {"key": "base_url", "value": f"https://{svc_lower}.ai.adports.ae", "enabled": True},
            {"key": "keycloak_url", "value": "https://auth.ai.adports.ae", "enabled": True},
            {"key": "realm", "value": "ai-portal", "enabled": True},
            {"key": "client_id", "value": f"{svc_lower}-readonly-test-client", "enabled": True},
            {"key": "client_secret", "value": "{{REPLACE_FROM_VAULT}}", "enabled": True},
            {"key": "auth_token", "value": "", "enabled": True},
        ],
        "_postman_variable_scope": "environment",
    }, indent=2)
    return {"environment_dev": dev_env, "environment_staging": staging_env, "environment_prod": prod_env}


async def generate_newman_config(state: IntegrationTestState) -> dict:
    svc_lower = state["service_name"].lower()
    newman_config = f"""\
#!/bin/bash
# Newman integration test runner for {state['service_name']}
# Usage: ENVIRONMENT=dev ./run-integration-tests.sh

ENVIRONMENT="${{ENVIRONMENT:-dev}}"
COLLECTION="./postman/{svc_lower}-collection.json"
ENV_FILE="./postman/environments/{svc_lower}-${{ENVIRONMENT}}.json"
RESULTS_DIR="./test-results/newman"

mkdir -p "$RESULTS_DIR"

# Inject secrets from Vault
if command -v vault &> /dev/null; then
  CLIENT_SECRET=$(vault kv get -field=client_secret "secret/{svc_lower}/test-client")
  export NEWMAN_CLIENT_SECRET="$CLIENT_SECRET"
fi

newman run "$COLLECTION" \\
  --environment "$ENV_FILE" \\
  --env-var "client_secret=$NEWMAN_CLIENT_SECRET" \\
  --reporters cli,junit,htmlextra \\
  --reporter-junit-export "$RESULTS_DIR/junit.xml" \\
  --reporter-htmlextra-export "$RESULTS_DIR/report.html" \\
  --timeout-request 10000 \\
  --delay-request 100 \\
  --bail \\
  --color on

EXIT_CODE=$?

# Upload results to Portal API
if [ $EXIT_CODE -eq 0 ]; then
  STATUS="passed"
else
  STATUS="failed"
fi

curl -s -X POST https://portal-api.ai.adports.ae/api/projects/{{}}/test-results \\
  -H "Content-Type: application/json" \\
  -H "Authorization: Bearer $PORTAL_API_TOKEN" \\
  -d '{{"type": "integration", "environment": "'"$ENVIRONMENT"'", "status": "'"$STATUS"'", "reportUrl": "'"$RESULTS_DIR/report.html"'"}}'

exit $EXIT_CODE
"""
    return {"newman_config": newman_config}


async def generate_test_data(state: IntegrationTestState) -> dict:
    prompt = f"""Generate test data JSON for integration testing '{state['service_name']}'.

OpenAPI spec:
{state['openapi_stub'][:1000]}

Generate:
- 5 valid request payloads for POST endpoints
- 3 invalid payloads (boundary conditions, missing required fields, wrong types)
- Lookup/reference data needed by the service

Output ONLY valid JSON as an object with 'valid', 'invalid', and 'reference_data' arrays."""
    data = await _llm(prompt)
    return {"test_data": data}


def _build_graph():
    g = StateGraph(IntegrationTestState)
    for name, fn in [
        ("generate_postman_collection", generate_postman_collection),
        ("generate_environments", generate_environments),
        ("generate_newman_config", generate_newman_config),
        ("generate_test_data", generate_test_data),
    ]:
        g.add_node(name, fn)
    g.add_edge("generate_postman_collection", "generate_environments")
    g.add_edge("generate_environments", "generate_newman_config")
    g.add_edge("generate_newman_config", "generate_test_data")
    g.add_edge("generate_test_data", END)
    g.set_entry_point("generate_postman_collection")
    return g.compile()


_graph = _build_graph()

app = FastAPI(title="ORBIT Integration Test Agent", version="1.0.0")
FastAPIInstrumentor.instrument_app(app)


class IntegrationTestRequest(BaseModel):
    project_id: str
    service_name: str
    openapi_stub: str = ""
    integration_scenarios: list[str] = []


@app.post("/api/generate/integration-tests")
async def generate_integration_tests(req: IntegrationTestRequest):
    """Generate Postman collection, environment files, Newman runner, and test data."""
    initial: IntegrationTestState = {
        "project_id": req.project_id,
        "service_name": req.service_name,
        "openapi_stub": req.openapi_stub,
        "integration_scenarios": req.integration_scenarios,
        "postman_collection": "",
        "environment_dev": "",
        "environment_staging": "",
        "environment_prod": "",
        "newman_config": "",
        "test_data": "",
    }
    result = await _graph.ainvoke(initial)
    try:
        async with httpx.AsyncClient(timeout=5) as client:
            await client.post(f"{settings.ledger_url}/api/ledger", json={
                "project_id": req.project_id,
                "pipeline_run_id": f"itest-gen-{req.service_name}",
                "stage": "integration_test_generation",
                "actor": "integration-test-agent",
                "status": "success",
                "metadata": {"service_name": req.service_name},
            })
    except Exception:
        pass
    return {
        "project_id": result["project_id"],
        "service_name": result["service_name"],
        "artifacts": {
            "postman_collection": result["postman_collection"],
            "environments": {
                "dev": result["environment_dev"],
                "staging": result["environment_staging"],
                "prod": result["environment_prod"],
            },
            "newman_config": result["newman_config"],
            "test_data": result["test_data"],
        },
    }


@app.get("/health/live")
async def liveness():
    return {"status": "ok"}


@app.get("/health/ready")
async def readiness():
    return {"status": "ok"}
