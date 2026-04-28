"""Fleet Upgrade Agent — analyses K8s fleet, generates migration plans."""
from __future__ import annotations

import json
import logging
import httpx
from fastapi import FastAPI
from opentelemetry.instrumentation.fastapi import FastAPIInstrumentor
from pydantic import BaseModel
from pydantic_settings import BaseSettings, SettingsConfigDict
import litellm

logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO)


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_prefix="FLEET_", env_file=".env", extra="ignore")
    kubernetes_mcp_url: str = "http://kubernetes-mcp.ai-portal.svc:8000"
    harbor_mcp_url: str = "http://harbor-mcp.ai-portal.svc:8000"
    litellm_api_base: str = "http://litellm-gateway.ai-portal.svc:4000"
    litellm_api_key: str = "changeme"
    default_model: str = "gpt-4o-mini"


settings = Settings()
litellm.api_base = settings.litellm_api_base
litellm.api_key  = settings.litellm_api_key

app = FastAPI(title="ORBIT Fleet Upgrade Agent", version="1.0.0")
FastAPIInstrumentor.instrument_app(app)


class FleetScanRequest(BaseModel):
    namespace: str = "ai-portal"


@app.post("/api/fleet-scan")
async def fleet_scan(req: FleetScanRequest):
    async with httpx.AsyncClient(timeout=30) as client:
        pods_r = await client.post(
            f"{settings.kubernetes_mcp_url}/tools/list_pods",
            json={"namespace": req.namespace},
        )
    pods_data = pods_r.json() if pods_r.status_code == 200 else {}

    prompt = f"""Analyse this Kubernetes fleet inventory from namespace '{req.namespace}'.
Identify:
1. Services running outdated images (look for :latest tags or old versions)
2. Services with no resource limits
3. Recommended upgrade actions with priority (P1/P2/P3)
4. Estimated effort for each upgrade

Fleet data:
{json.dumps(pods_data, indent=2)[:5000]}"""

    response = await litellm.acompletion(
        model=settings.default_model,
        messages=[{"role": "user", "content": prompt}],
        temperature=0.1,
    )
    return {
        "namespace": req.namespace,
        "upgrade_plan": response.choices[0].message.content,
    }


@app.get("/health/live")
async def liveness():
    return {"status": "ok"}
