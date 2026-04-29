"""Tests for frontend specialist agent."""
import pytest
from unittest.mock import AsyncMock, patch, MagicMock


@pytest.mark.asyncio
async def test_plan_pages():
    from app.main import plan_pages
    state = {
        "project_id": "p1", "mfe_name": "payments-mfe",
        "openapi_stubs": [], "user_journeys": ["As a user, I can view a list of payments"],
        "pages": [], "components": [], "routing_module": "",
        "i18n_en": "", "i18n_ar": "", "dockerfile": "",
        "nginx_conf": "", "jest_tests": [],
    }
    with patch("app.main.litellm.acompletion", new_callable=AsyncMock) as mock:
        mock.return_value = MagicMock(choices=[MagicMock(message=MagicMock(
            content='[{"name": "PaymentListPage", "route": "/payments", "components": ["PaymentTableComponent"]}]'
        ))])
        result = await plan_pages(state)
    assert len(result["pages"]) == 1
    assert result["pages"][0]["name"] == "PaymentListPage"


@pytest.mark.asyncio
async def test_generate_dockerfile_and_nginx():
    from app.main import generate_dockerfile_and_nginx
    state = {
        "project_id": "p1", "mfe_name": "payments-mfe",
        "openapi_stubs": [], "user_journeys": [],
        "pages": [], "components": [], "routing_module": "",
        "i18n_en": "", "i18n_ar": "", "dockerfile": "",
        "nginx_conf": "", "jest_tests": [],
    }
    result = await generate_dockerfile_and_nginx(state)
    assert "harbor.ai.adports.ae/orbit/node:20-slim" in result["dockerfile"]
    assert "payments-mfe" in result["dockerfile"]
    assert "nginx" in result["nginx_conf"]
