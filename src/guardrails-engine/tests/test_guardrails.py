"""Tests for guardrails engine."""
import pytest
from unittest.mock import AsyncMock, patch, MagicMock
from fastapi.testclient import TestClient


def test_forbidden_action_denied():
    from app.main import app
    client = TestClient(app)
    with patch("app.main.evaluate_policy", new_callable=AsyncMock) as mock_opa:
        mock_opa.return_value = {"allow": True}
        resp = client.post("/api/guardrails/evaluate", json={
            "action_type": "delete_production_db",
            "actor_id": "user-123",
            "actor_roles": ["orbit-admin"],
            "project_id": "proj-1",
            "project_type": "payment",
            "agent_name": "backend-specialist-agent",
            "estimated_cost_usd": 1.0,
        })
    assert resp.status_code == 200
    data = resp.json()
    assert data["allowed"] is False
    assert "forbidden" in data["reason"].lower()


@pytest.mark.asyncio
async def test_redact_credit_card():
    from app.main import redact_sensitive_data
    text = "Process payment for card 4532 1234 5678 9010 with CVV 123"
    redacted, fields = await redact_sensitive_data(text)
    assert "4532 1234 5678 9010" not in redacted
    assert "[REDACTED]" in redacted
    assert len(fields) > 0


def test_budget_exceeded_denied():
    from app.main import app
    client = TestClient(app)
    with patch("app.main.evaluate_policy", new_callable=AsyncMock) as mock_opa:
        mock_opa.return_value = {"allow": True}
        resp = client.post("/api/guardrails/evaluate", json={
            "action_type": "generate_code",
            "actor_id": "user-123",
            "actor_roles": ["orbit-developer"],
            "project_id": "proj-1",
            "project_type": "crm",
            "agent_name": "backend-specialist-agent",
            "estimated_cost_usd": 99.0,  # exceeds $10 default
        })
    assert resp.status_code == 200
    assert resp.json()["allowed"] is False
    assert "budget" in resp.json()["reason"].lower()
