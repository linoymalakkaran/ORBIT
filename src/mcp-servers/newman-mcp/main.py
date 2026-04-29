"""
Phase 09 – G09: Newman / Postman MCP Server
FastAPI service exposing Postman collection generation and Newman execution
as MCP tools callable by ORBIT agents.
"""
import os
import json
import uuid
import subprocess
import tempfile
from typing import Any
import httpx
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel

LITELLM_URL   = os.environ.get("LITELLM_URL",    "http://litellm-gateway.litellm.svc:4000")
LITELLM_KEY   = os.environ.get("LITELLM_API_KEY", "")
DEFAULT_MODEL = os.environ.get("NEWMAN_MODEL",    "gpt-4o-mini")
PORTAL_API    = os.environ.get("PORTAL_API_URL",  "http://portal-api.ai-portal.svc:80")
VAULT_ADDR    = os.environ.get("VAULT_ADDR",      "http://vault.vault.svc:8200")

app = FastAPI(title="Newman MCP", version="1.0.0")

# In-memory store for collections and run reports
_collections: dict[str, dict] = {}
_reports:     dict[str, dict] = {}


# ── Models ────────────────────────────────────────────────────────────────────

class GenerateCollectionRequest(BaseModel):
    project_id: str
    openapi_spec_url: str
    environments: list[str] = ["dev", "staging"]


class RunCollectionRequest(BaseModel):
    collection_id: str
    environment: str = "dev"
    base_url: str


class UploadResultsRequest(BaseModel):
    run_id: str
    project_id: str


class GetEnvironmentRequest(BaseModel):
    project_id: str
    env_name: str


# ── Health ────────────────────────────────────────────────────────────────────

@app.get("/health/live")
async def live():
    return {"status": "healthy"}


@app.get("/health/ready")
async def ready():
    try:
        result = subprocess.run(["newman", "--version"], capture_output=True, timeout=5)
        return {"status": "healthy" if result.returncode == 0 else "degraded", "newman": result.stdout.decode().strip()}
    except (FileNotFoundError, subprocess.TimeoutExpired):
        return {"status": "degraded", "note": "newman binary not found"}


# ── LLM helper ───────────────────────────────────────────────────────────────

async def _llm(prompt: str) -> str:
    async with httpx.AsyncClient() as c:
        r = await c.post(
            f"{LITELLM_URL}/chat/completions",
            headers={"Authorization": f"Bearer {LITELLM_KEY}"},
            json={
                "model": DEFAULT_MODEL,
                "messages": [
                    {"role": "system", "content": "Return only valid Postman Collection v2.1 JSON. No explanation."},
                    {"role": "user", "content": prompt},
                ],
                "temperature": 0.0,
            },
            timeout=60,
        )
        r.raise_for_status()
        return r.json()["choices"][0]["message"]["content"].strip()


# ── Tool 1: generate_collection ──────────────────────────────────────────────

@app.post("/tools/generate_collection")
async def generate_collection(req: GenerateCollectionRequest) -> dict[str, Any]:
    """Generates a Postman Collection v2.1 JSON from an OpenAPI spec URL."""
    async with httpx.AsyncClient() as c:
        r = await c.get(req.openapi_spec_url, timeout=10)
        r.raise_for_status()
        spec_text = r.text[:8000]  # truncate to fit context window

    prompt = f"""
Convert the following OpenAPI spec into a Postman Collection v2.1 JSON.
Include:
- All endpoints as request items
- Pre-request script setting {{{{base_url}}}} from environment
- Test scripts asserting status code 200 or 201 for happy paths
- Example request bodies from the spec
- Grouped by tag/resource

OpenAPI spec:
{spec_text}
    """
    collection_json = await _llm(prompt)
    try:
        collection = json.loads(collection_json)
    except json.JSONDecodeError:
        raise HTTPException(500, "LLM returned invalid JSON for Postman collection")

    cid = str(uuid.uuid4())
    _collections[cid] = {"id": cid, "project_id": req.project_id, "collection": collection}
    return {"collection_id": cid, "project_id": req.project_id, "item_count": len(collection.get("item", []))}


# ── Tool 2: run_collection ────────────────────────────────────────────────────

@app.post("/tools/run_collection")
async def run_collection(req: RunCollectionRequest) -> dict[str, Any]:
    """Runs a Postman collection using Newman against the specified base URL."""
    if req.collection_id not in _collections:
        raise HTTPException(404, f"Collection '{req.collection_id}' not found")

    collection = _collections[req.collection_id]["collection"]

    with tempfile.TemporaryDirectory() as tmpdir:
        col_file   = f"{tmpdir}/collection.json"
        report_file = f"{tmpdir}/report.json"

        with open(col_file, "w") as f:
            json.dump(collection, f)

        env_vars = {"base_url": req.base_url}
        env_file = f"{tmpdir}/env.json"
        with open(env_file, "w") as f:
            json.dump({
                "id": str(uuid.uuid4()),
                "name": req.environment,
                "values": [{"key": k, "value": v, "enabled": True} for k, v in env_vars.items()],
            }, f)

        result = subprocess.run(
            [
                "newman", "run", col_file,
                "--environment", env_file,
                "--reporters", "json",
                "--reporter-json-export", report_file,
                "--timeout-request", "10000",
            ],
            capture_output=True,
            timeout=120,
        )

        run_id = str(uuid.uuid4())
        try:
            with open(report_file) as f:
                report = json.load(f)
        except (FileNotFoundError, json.JSONDecodeError):
            report = {}

        stats = report.get("run", {}).get("stats", {})
        _reports[run_id] = {"run_id": run_id, "collection_id": req.collection_id, "report": report}

        return {
            "run_id": run_id,
            "collection_id": req.collection_id,
            "environment": req.environment,
            "base_url": req.base_url,
            "passed": stats.get("assertions", {}).get("passed", 0),
            "failed": stats.get("assertions", {}).get("failed", 0),
            "duration_ms": report.get("run", {}).get("timings", {}).get("completed", 0),
            "exit_code": result.returncode,
        }


# ── Tool 3: get_run_report ────────────────────────────────────────────────────

@app.get("/tools/get_run_report")
async def get_run_report(run_id: str) -> dict[str, Any]:
    """Returns the full Newman run report for a previous run."""
    if run_id not in _reports:
        raise HTTPException(404, f"Run '{run_id}' not found")
    return _reports[run_id]


# ── Tool 4: upload_to_portal ──────────────────────────────────────────────────

@app.post("/tools/upload_to_portal")
async def upload_to_portal(req: UploadResultsRequest) -> dict[str, Any]:
    """Posts Newman run results to the Portal API as a test artifact."""
    if req.run_id not in _reports:
        raise HTTPException(404, f"Run '{req.run_id}' not found")
    report = _reports[req.run_id]

    async with httpx.AsyncClient() as c:
        r = await c.post(
            f"{PORTAL_API}/api/v1/projects/{req.project_id}/artifacts",
            json={
                "type": "TestReport",
                "source": "newman",
                "run_id": req.run_id,
                "content": json.dumps(report["report"])[:50000],
            },
            timeout=15,
        )
        if r.status_code not in (200, 201):
            raise HTTPException(502, f"Portal API returned {r.status_code}")
        return {"success": True, "artifact_id": r.json().get("id"), "run_id": req.run_id}


# ── Tool 5: list_collections ──────────────────────────────────────────────────

@app.get("/tools/list_collections")
async def list_collections(project_id: str) -> dict[str, Any]:
    """Lists all collections for a project."""
    cols = [
        {"collection_id": k, "project_id": v["project_id"]}
        for k, v in _collections.items()
        if v["project_id"] == project_id
    ]
    return {"project_id": project_id, "collections": cols}


# ── Tool 6: get_environment ───────────────────────────────────────────────────

@app.get("/tools/get_environment")
async def get_environment(project_id: str, env_name: str) -> dict[str, Any]:
    """Returns a Postman environment file with base_url set for the given environment."""
    env_urls = {"dev": "http://api-dev.ai.adports.ae", "staging": "http://api-staging.ai.adports.ae"}
    base_url = env_urls.get(env_name, f"http://api-{env_name}.ai.adports.ae")
    return {
        "project_id": project_id,
        "env_name": env_name,
        "environment": {
            "id": str(uuid.uuid4()),
            "name": f"{project_id}-{env_name}",
            "values": [
                {"key": "base_url", "value": base_url, "enabled": True},
                {"key": "project_id", "value": project_id, "enabled": True},
            ],
        },
    }
