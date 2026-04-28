"""ORBIT Integration Tests — end-to-end pipeline smoke tests."""
import asyncio
import os
import time

import httpx
import pytest

BASE_PORTAL_API = os.getenv("PORTAL_API_URL", "https://api.ai.adports.ae")
BASE_LEDGER = os.getenv("LEDGER_API_URL", "http://pipeline-ledger.ai-portal.svc:8000")
BASE_ORCHESTRATOR = os.getenv("ORCHESTRATOR_URL", "http://orchestrator.ai-portal.svc:8000")
BASE_CAPABILITY = os.getenv("CAPABILITY_URL", "http://capability-fabric.ai-portal.svc:8000")
KC_TOKEN_URL = os.getenv("KC_TOKEN_URL", "https://auth.ai.adports.ae/realms/ai-portal/protocol/openid-connect/token")
KC_CLIENT_ID = os.getenv("KC_CLIENT_ID", "portal-api")
KC_USERNAME = os.getenv("KC_USERNAME", "integration-test-user")
KC_PASSWORD = os.getenv("KC_PASSWORD", "")


@pytest.fixture(scope="session")
def event_loop():
    loop = asyncio.new_event_loop()
    yield loop
    loop.close()


@pytest.fixture(scope="session")
async def auth_token() -> str:
    async with httpx.AsyncClient() as client:
        r = await client.post(KC_TOKEN_URL, data={
            "grant_type": "password",
            "client_id": KC_CLIENT_ID,
            "username": KC_USERNAME,
            "password": KC_PASSWORD,
        })
    r.raise_for_status()
    return r.json()["access_token"]


@pytest.fixture(scope="session")
async def authed_client(auth_token: str):
    async with httpx.AsyncClient(headers={"Authorization": f"Bearer {auth_token}"}, timeout=30) as c:
        yield c


@pytest.mark.asyncio
async def test_portal_api_health(authed_client):
    r = await authed_client.get(f"{BASE_PORTAL_API}/health/live")
    assert r.status_code == 200, r.text


@pytest.mark.asyncio
async def test_list_projects(authed_client):
    r = await authed_client.get(f"{BASE_PORTAL_API}/api/projects")
    assert r.status_code == 200
    data = r.json()
    assert "items" in data or isinstance(data, list)


@pytest.mark.asyncio
async def test_capability_fabric_list_skills(authed_client):
    r = await authed_client.get(f"{BASE_CAPABILITY}/api/skills")
    assert r.status_code == 200
    skills = r.json()
    assert len(skills) > 0, "No skills registered"


@pytest.mark.asyncio
async def test_ledger_append_and_verify(authed_client):
    """Append a ledger entry, then verify the chain is valid."""
    payload = {
        "project_id": "integration-test-project",
        "pipeline_run_id": f"test-run-{int(time.time())}",
        "stage": "test_generation",
        "actor": "integration-test",
        "status": "success",
        "metadata": {"test": True},
    }
    r = await authed_client.post(f"{BASE_LEDGER}/api/ledger", json=payload)
    assert r.status_code in (200, 201), r.text

    r2 = await authed_client.get(f"{BASE_LEDGER}/api/ledger/verify?project_id=integration-test-project")
    assert r2.status_code == 200
    result = r2.json()
    assert result.get("chain_valid") is True


@pytest.mark.asyncio
async def test_orchestrator_start_pipeline(authed_client):
    """Start a lightweight pipeline run and verify workflow id is returned."""
    body = {
        "project_id": "integration-test-project",
        "stages": ["requirements_analysis"],
        "context": "Smoke test pipeline run",
    }
    r = await authed_client.post(f"{BASE_ORCHESTRATOR}/api/pipelines", json=body)
    assert r.status_code in (200, 201, 202), r.text
    data = r.json()
    assert "workflow_id" in data or "pipeline_id" in data


@pytest.mark.asyncio
async def test_pr_review_agent_health():
    async with httpx.AsyncClient(timeout=10) as c:
        r = await c.get(f"{os.getenv('PR_REVIEW_URL', 'http://pr-review-agent.ai-portal.svc:8000')}/health/live")
    assert r.status_code == 200


@pytest.mark.asyncio
async def test_health_monitor_check():
    async with httpx.AsyncClient(timeout=10) as c:
        r = await c.get(f"{os.getenv('HEALTH_MONITOR_URL', 'http://health-monitor-agent.ai-portal.svc:8000')}/api/health/check")
    assert r.status_code == 200
    data = r.json()
    assert "healthy" in data
