"""Tests for integration test agent."""
import pytest
import json
from unittest.mock import AsyncMock, patch, MagicMock


@pytest.mark.asyncio
async def test_generate_environments():
    from app.main import generate_environments
    state = {
        "project_id": "p1", "service_name": "PaymentService",
        "openapi_stub": "", "integration_scenarios": [],
        "postman_collection": "", "environment_dev": "",
        "environment_staging": "", "environment_prod": "",
        "newman_config": "", "test_data": "",
    }
    result = await generate_environments(state)
    dev_env = json.loads(result["environment_dev"])
    assert dev_env["name"] == "PaymentService — Dev"
    keys = {v["key"] for v in dev_env["values"]}
    assert "base_url" in keys
    assert "client_secret" in keys


@pytest.mark.asyncio
async def test_generate_newman_config():
    from app.main import generate_newman_config
    state = {
        "project_id": "p1", "service_name": "PaymentService",
        "openapi_stub": "", "integration_scenarios": [],
        "postman_collection": "", "environment_dev": "",
        "environment_staging": "", "environment_prod": "",
        "newman_config": "", "test_data": "",
    }
    result = await generate_newman_config(state)
    assert "newman run" in result["newman_config"]
    assert "junit" in result["newman_config"]
    assert "vault" in result["newman_config"].lower()
