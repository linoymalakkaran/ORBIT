"""Tests for backend specialist agent."""
import pytest
from unittest.mock import AsyncMock, patch, MagicMock


@pytest.mark.asyncio
async def test_generate_domain_entities():
    from app.main import generate_domain_entities
    state = {
        "project_id": "p1", "service_name": "PaymentService",
        "responsibility": "Process payments",
        "openapi_stub": "openapi: '3.1.0'",
        "domain_entities": [], "cqrs_handlers": [],
        "ef_context": "", "program_cs": "",
        "dockerfile": "", "helm_values": "", "unit_tests": [],
    }
    with patch("app.main.litellm.acompletion", new_callable=AsyncMock) as mock:
        mock.return_value = MagicMock(choices=[MagicMock(message=MagicMock(content="public class Payment { }"))])
        result = await generate_domain_entities(state)
    assert len(result["domain_entities"]) == 1
    assert "Payment" in result["domain_entities"][0]


@pytest.mark.asyncio
async def test_generate_dockerfile():
    from app.main import generate_dockerfile
    state = {
        "project_id": "p1", "service_name": "PaymentService",
        "responsibility": "", "openapi_stub": "",
        "domain_entities": [], "cqrs_handlers": [],
        "ef_context": "", "program_cs": "",
        "dockerfile": "", "helm_values": "", "unit_tests": [],
    }
    result = await generate_dockerfile(state)
    assert "harbor.ai.adports.ae/orbit/dotnet-sdk:9.0" in result["dockerfile"]
    assert "PaymentService.dll" in result["dockerfile"]
