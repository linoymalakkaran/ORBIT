"""Tests for service health monitor."""
import pytest
from unittest.mock import AsyncMock, patch, MagicMock
import json


@pytest.mark.asyncio
async def test_correlate_alerts_and_propose_remediation():
    from app.main import correlate_alerts_and_propose_remediation
    with patch("app.main.litellm.acompletion", new_callable=AsyncMock) as mock:
        mock.return_value = MagicMock(choices=[MagicMock(message=MagicMock(
            content='{"root_cause": "DB connection pool exhausted", "remediation_steps": ["Restart pod", "Scale up DB"], "long_term_fix": "Increase pool size", "severity": "HIGH"}'
        ))])
        result = await correlate_alerts_and_propose_remediation(
            service="payment-service",
            error_rate=12.5,
            p99_ms=3500,
            error_logs=["ERROR: connection refused to postgresql"],
        )
    assert result["severity"] == "HIGH"
    assert "root_cause" in result
    assert len(result["remediation_steps"]) > 0


def test_health_endpoints():
    from app.main import app
    from fastapi.testclient import TestClient
    client = TestClient(app)
    resp = client.get("/health/live")
    assert resp.status_code == 200
    assert resp.json()["status"] == "ok"
