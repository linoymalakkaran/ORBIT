"""Tests for QA agent."""
import pytest
from unittest.mock import AsyncMock, patch, MagicMock


@pytest.mark.asyncio
async def test_generate_k6_script():
    from app.main import generate_k6_script
    state = {
        "project_id": "p1", "service_name": "PaymentService",
        "openapi_stub": "openapi: 3.1.0", "acceptance_criteria": [],
        "performance_targets": {"p95_ms": 300, "rps": 200, "error_rate_pct": 0.5},
        "playwright_tests": [], "k6_script": "", "pact_consumer": "",
        "pact_provider": "", "axe_config": "", "visual_regression_config": "",
    }
    with patch("app.main.litellm.acompletion", new_callable=AsyncMock) as mock:
        mock.return_value = MagicMock(choices=[MagicMock(message=MagicMock(content="import http from 'k6/http';"))])
        result = await generate_k6_script(state)
    assert "k6" in result["k6_script"]


@pytest.mark.asyncio
async def test_generate_axe_and_visual():
    from app.main import generate_axe_and_visual
    state = {
        "project_id": "p1", "service_name": "PaymentService",
        "openapi_stub": "", "acceptance_criteria": [],
        "performance_targets": {}, "playwright_tests": [],
        "k6_script": "", "pact_consumer": "", "pact_provider": "",
        "axe_config": "", "visual_regression_config": "",
    }
    result = await generate_axe_and_visual(state)
    assert "wcag2aa" in result["axe_config"]
    assert "toHaveScreenshot" in result["visual_regression_config"]
