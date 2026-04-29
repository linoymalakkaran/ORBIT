"""
Phase 09 – G06: SonarQube MCP Server
FastAPI service exposing SonarQube as MCP tools callable by ORBIT agents.
"""
import os
import httpx
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from typing import Optional, Any

SONAR_URL   = os.environ["SONAR_URL"]    # e.g. http://sonarqube.sonarqube.svc:9000
SONAR_TOKEN = os.environ["SONAR_TOKEN"]  # SonarQube user/project token from Vault

app = FastAPI(title="SonarQube MCP", version="1.0.0")


def _auth() -> tuple[str, str]:
    return (SONAR_TOKEN, "")


# ── Models ───────────────────────────────────────────────────────────────────

class TriggerAnalysisRequest(BaseModel):
    project_key: str
    branch: str = "main"


class ConfigureQualityGateRequest(BaseModel):
    project_key: str
    gate_name: str


# ── Health ───────────────────────────────────────────────────────────────────

@app.get("/health/live")
async def live():
    return {"status": "healthy"}


@app.get("/health/ready")
async def ready():
    async with httpx.AsyncClient() as c:
        r = await c.get(f"{SONAR_URL}/api/system/ping", auth=_auth(), timeout=5)
        return {"status": "healthy" if r.status_code == 200 else "degraded"}


# ── Tool 1: get_quality_gate_status ──────────────────────────────────────────

@app.get("/tools/get_quality_gate_status")
async def get_quality_gate_status(project_key: str) -> dict[str, Any]:
    """Returns the current quality gate status for a project."""
    async with httpx.AsyncClient() as c:
        r = await c.get(
            f"{SONAR_URL}/api/qualitygates/project_status",
            params={"projectKey": project_key},
            auth=_auth(),
            timeout=10,
        )
        if r.status_code == 404:
            raise HTTPException(404, f"Project '{project_key}' not found in SonarQube")
        r.raise_for_status()
        data = r.json()
        gate = data.get("projectStatus", {})
        return {
            "project_key": project_key,
            "status": gate.get("status", "UNKNOWN"),           # "OK" | "ERROR" | "WARN"
            "conditions": gate.get("conditions", []),
            "ignored_conditions": gate.get("ignoredConditions", False),
        }


# ── Tool 2: trigger_analysis ─────────────────────────────────────────────────

@app.post("/tools/trigger_analysis")
async def trigger_analysis(req: TriggerAnalysisRequest) -> dict[str, Any]:
    """Triggers a SonarQube analysis via CI integration (requires scanner to be pre-configured)."""
    async with httpx.AsyncClient() as c:
        # SonarQube does not have a direct "trigger" REST endpoint —
        # we create a background task record and return. The actual
        # scanner must be invoked in the CI pipeline.
        r = await c.post(
            f"{SONAR_URL}/api/project_analyses/search",
            params={"project": req.project_key, "branch": req.branch, "ps": "1"},
            auth=_auth(),
            timeout=10,
        )
        r.raise_for_status()
        analyses = r.json().get("analyses", [])
        last_analysis = analyses[0] if analyses else None
        return {
            "project_key": req.project_key,
            "branch": req.branch,
            "status": "QUEUED",
            "last_analysis_date": last_analysis.get("date") if last_analysis else None,
            "note": "Trigger the sonar-scanner from your CI pipeline using the project key.",
        }


# ── Tool 3: get_issues ───────────────────────────────────────────────────────

@app.get("/tools/get_issues")
async def get_issues(
    project_key: str,
    severities: Optional[str] = "BLOCKER,CRITICAL,MAJOR",
    resolved: bool = False,
    page: int = 1,
    page_size: int = 50,
) -> dict[str, Any]:
    """Returns SonarQube issues (bugs, vulnerabilities, code smells) for a project."""
    params: dict[str, Any] = {
        "componentKeys": project_key,
        "severities": severities,
        "resolved": str(resolved).lower(),
        "p": page,
        "ps": page_size,
    }
    async with httpx.AsyncClient() as c:
        r = await c.get(f"{SONAR_URL}/api/issues/search", params=params, auth=_auth(), timeout=15)
        r.raise_for_status()
        data = r.json()
        issues = [
            {
                "key": i.get("key"),
                "message": i.get("message"),
                "severity": i.get("severity"),
                "type": i.get("type"),
                "component": i.get("component"),
                "line": i.get("line"),
                "status": i.get("status"),
                "rule": i.get("rule"),
            }
            for i in data.get("issues", [])
        ]
        return {
            "project_key": project_key,
            "total": data.get("total", 0),
            "page": page,
            "page_size": page_size,
            "issues": issues,
        }


# ── Tool 4: get_metrics ──────────────────────────────────────────────────────

@app.get("/tools/get_metrics")
async def get_metrics(project_key: str) -> dict[str, Any]:
    """Returns key quality metrics for a SonarQube project."""
    metric_keys = "coverage,duplicated_lines_density,bugs,vulnerabilities,code_smells,security_hotspots,reliability_rating,security_rating,sqale_rating"
    async with httpx.AsyncClient() as c:
        r = await c.get(
            f"{SONAR_URL}/api/measures/component",
            params={"component": project_key, "metricKeys": metric_keys},
            auth=_auth(),
            timeout=10,
        )
        r.raise_for_status()
        data = r.json()
        metrics = {
            m["metric"]: m.get("value") or m.get("periods", [{}])[0].get("value")
            for m in data.get("component", {}).get("measures", [])
        }
        return {"project_key": project_key, "metrics": metrics}


# ── Tool 5: configure_quality_gate ───────────────────────────────────────────

@app.post("/tools/configure_quality_gate")
async def configure_quality_gate(req: ConfigureQualityGateRequest) -> dict[str, Any]:
    """Assigns a quality gate to a SonarQube project."""
    async with httpx.AsyncClient() as c:
        # First, find the gate ID by name
        r = await c.get(f"{SONAR_URL}/api/qualitygates/list", auth=_auth(), timeout=10)
        r.raise_for_status()
        gates = r.json().get("qualitygates", [])
        gate = next((g for g in gates if g.get("name") == req.gate_name), None)
        if not gate:
            raise HTTPException(404, f"Quality gate '{req.gate_name}' not found")

        # Associate gate with project
        r2 = await c.post(
            f"{SONAR_URL}/api/qualitygates/select",
            params={"projectKey": req.project_key, "gateId": gate["id"]},
            auth=_auth(),
            timeout=10,
        )
        r2.raise_for_status()
        return {"success": True, "project_key": req.project_key, "gate_name": req.gate_name, "gate_id": gate["id"]}
