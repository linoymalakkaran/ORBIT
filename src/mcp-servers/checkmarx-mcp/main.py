"""
Phase 09 – G07: Checkmarx MCP Server
FastAPI service exposing Checkmarx SAST as MCP tools callable by ORBIT agents.
Uses Checkmarx One (CxOne) REST API v3.
"""
import os
import httpx
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from typing import Any, Optional

CHECKMARX_URL           = os.environ["CHECKMARX_URL"]            # e.g. https://checkmarx.adports.ae
CHECKMARX_CLIENT_ID     = os.environ["CHECKMARX_CLIENT_ID"]
CHECKMARX_CLIENT_SECRET = os.environ["CHECKMARX_CLIENT_SECRET"]

app = FastAPI(title="Checkmarx MCP", version="1.0.0")

_token_cache: dict[str, str] = {}


async def _get_token() -> str:
    """Obtain (and cache) a Checkmarx OAuth2 access token."""
    if _token_cache.get("token"):
        return _token_cache["token"]
    async with httpx.AsyncClient() as c:
        r = await c.post(
            f"{CHECKMARX_URL}/auth/realms/organization/protocol/openid-connect/token",
            data={
                "grant_type": "client_credentials",
                "client_id": CHECKMARX_CLIENT_ID,
                "client_secret": CHECKMARX_CLIENT_SECRET,
            },
            timeout=10,
        )
        r.raise_for_status()
        token = r.json()["access_token"]
        _token_cache["token"] = token
        return token


def _headers(token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}


# ── Models ───────────────────────────────────────────────────────────────────

class TriggerSastScanRequest(BaseModel):
    project_name: str
    repo_url: str
    branch: str = "main"


class ConfigurePresetRequest(BaseModel):
    project_name: str
    preset_name: str = "Checkmarx Default"


# ── Health ───────────────────────────────────────────────────────────────────

@app.get("/health/live")
async def live():
    return {"status": "healthy"}


@app.get("/health/ready")
async def ready():
    try:
        await _get_token()
        return {"status": "healthy"}
    except Exception:
        return {"status": "degraded"}


# ── Tool 1: trigger_sast_scan ─────────────────────────────────────────────────

@app.post("/tools/trigger_sast_scan")
async def trigger_sast_scan(req: TriggerSastScanRequest) -> dict[str, Any]:
    """Triggers a Checkmarx SAST scan for the given repository and branch."""
    token = await _get_token()
    # Resolve project ID
    async with httpx.AsyncClient() as c:
        rp = await c.get(
            f"{CHECKMARX_URL}/api/projects",
            params={"name": req.project_name},
            headers=_headers(token),
            timeout=10,
        )
        rp.raise_for_status()
        projects = rp.json().get("projects", [])
        if not projects:
            raise HTTPException(404, f"Project '{req.project_name}' not found in Checkmarx")
        project_id = projects[0]["id"]

        # Create scan
        rs = await c.post(
            f"{CHECKMARX_URL}/api/scans",
            json={
                "project": {"id": project_id},
                "type": "sast",
                "branch": req.branch,
                "engines": ["sast"],
                "tags": {"source": "orbit-mcp"},
            },
            headers=_headers(token),
            timeout=15,
        )
        rs.raise_for_status()
        scan = rs.json()
        return {
            "scan_id": scan.get("id"),
            "project_id": project_id,
            "project_name": req.project_name,
            "branch": req.branch,
            "status": scan.get("status", "Running"),
        }


# ── Tool 2: get_scan_results ─────────────────────────────────────────────────

@app.get("/tools/get_scan_results")
async def get_scan_results(scan_id: str) -> dict[str, Any]:
    """Returns SAST findings for a completed scan."""
    token = await _get_token()
    async with httpx.AsyncClient() as c:
        r = await c.get(
            f"{CHECKMARX_URL}/api/results",
            params={"scan-id": scan_id, "limit": 500},
            headers=_headers(token),
            timeout=15,
        )
        r.raise_for_status()
        data = r.json()
        findings = [
            {
                "id": f.get("id"),
                "severity": f.get("severity"),
                "cwe_id": f.get("vulnerabilityDetails", {}).get("cweId"),
                "file": f.get("data", {}).get("fileName"),
                "line": f.get("data", {}).get("line"),
                "description": f.get("description"),
                "query_name": f.get("queryName"),
                "status": f.get("state"),
            }
            for f in data.get("results", [])
        ]
        return {
            "scan_id": scan_id,
            "total": data.get("totalCount", len(findings)),
            "findings": findings,
        }


# ── Tool 3: get_project_last_scan ────────────────────────────────────────────

@app.get("/tools/get_project_last_scan")
async def get_project_last_scan(project_name: str) -> dict[str, Any]:
    """Returns the summary of the most recent scan for a project."""
    token = await _get_token()
    async with httpx.AsyncClient() as c:
        rp = await c.get(
            f"{CHECKMARX_URL}/api/projects",
            params={"name": project_name},
            headers=_headers(token),
            timeout=10,
        )
        rp.raise_for_status()
        projects = rp.json().get("projects", [])
        if not projects:
            raise HTTPException(404, f"Project '{project_name}' not found")
        project_id = projects[0]["id"]

        rs = await c.get(
            f"{CHECKMARX_URL}/api/scans",
            params={"project-id": project_id, "statuses": "Completed", "limit": 1, "sort": "-createdAt"},
            headers=_headers(token),
            timeout=10,
        )
        rs.raise_for_status()
        scans = rs.json().get("scans", [])
        if not scans:
            return {"project_name": project_name, "scan": None}
        scan = scans[0]
        return {
            "project_name": project_name,
            "scan_id": scan.get("id"),
            "status": scan.get("status"),
            "created_at": scan.get("createdAt"),
            "branch": scan.get("branch"),
            "total_findings": scan.get("statusDetails", {}).get("total", 0),
            "critical": scan.get("statusDetails", {}).get("critical", 0),
            "high": scan.get("statusDetails", {}).get("high", 0),
        }


# ── Tool 4: configure_preset ─────────────────────────────────────────────────

@app.post("/tools/configure_preset")
async def configure_preset(req: ConfigurePresetRequest) -> dict[str, Any]:
    """Assigns a scan preset to a Checkmarx project."""
    token = await _get_token()
    async with httpx.AsyncClient() as c:
        rp = await c.get(
            f"{CHECKMARX_URL}/api/projects",
            params={"name": req.project_name},
            headers=_headers(token),
            timeout=10,
        )
        rp.raise_for_status()
        projects = rp.json().get("projects", [])
        if not projects:
            raise HTTPException(404, f"Project '{req.project_name}' not found")
        project_id = projects[0]["id"]

        r = await c.put(
            f"{CHECKMARX_URL}/api/projects/{project_id}",
            json={"configuration": {"preset": req.preset_name}},
            headers=_headers(token),
            timeout=10,
        )
        r.raise_for_status()
        return {"success": True, "project_name": req.project_name, "preset_name": req.preset_name}


# ── Tool 5: get_findings_by_severity ─────────────────────────────────────────

@app.get("/tools/get_findings_by_severity")
async def get_findings_by_severity(
    project_name: str,
    severity: str = "HIGH",
    limit: int = 100,
) -> dict[str, Any]:
    """Returns findings filtered by severity for the last completed scan of a project."""
    token = await _get_token()
    async with httpx.AsyncClient() as c:
        rp = await c.get(
            f"{CHECKMARX_URL}/api/projects",
            params={"name": project_name},
            headers=_headers(token),
            timeout=10,
        )
        rp.raise_for_status()
        projects = rp.json().get("projects", [])
        if not projects:
            raise HTTPException(404, f"Project '{project_name}' not found")
        project_id = projects[0]["id"]

        rs = await c.get(
            f"{CHECKMARX_URL}/api/scans",
            params={"project-id": project_id, "statuses": "Completed", "limit": 1, "sort": "-createdAt"},
            headers=_headers(token),
            timeout=10,
        )
        rs.raise_for_status()
        scans = rs.json().get("scans", [])
        if not scans:
            raise HTTPException(404, "No completed scans found for this project")

        scan_id = scans[0]["id"]
        rf = await c.get(
            f"{CHECKMARX_URL}/api/results",
            params={"scan-id": scan_id, "severity": severity, "limit": limit},
            headers=_headers(token),
            timeout=15,
        )
        rf.raise_for_status()
        data = rf.json()
        return {
            "project_name": project_name,
            "scan_id": scan_id,
            "severity_filter": severity,
            "total": data.get("totalCount", 0),
            "findings": data.get("results", []),
        }
