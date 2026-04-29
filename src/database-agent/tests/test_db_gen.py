"""Tests for database agent."""
import pytest
from unittest.mock import AsyncMock, patch, MagicMock


@pytest.mark.asyncio
async def test_generate_migrations():
    from app.main import generate_migrations
    state = {
        "project_id": "p1", "service_name": "PaymentService",
        "domain_entities": "public class Payment { public Guid Id { get; private set; } }",
        "openfga_model": "",
        "migrations": [], "rls_policies": [],
        "index_recommendations": [], "seed_scripts": [],
    }
    with patch("app.main.litellm.acompletion", new_callable=AsyncMock) as mock:
        mock.return_value = MagicMock(choices=[MagicMock(message=MagicMock(content="CREATE TABLE payments (id UUID PRIMARY KEY);"))])
        result = await generate_migrations(state)
    assert len(result["migrations"]) == 1
    assert "CREATE TABLE" in result["migrations"][0] or "migration" in result["migrations"][0].lower()


@pytest.mark.asyncio
async def test_generate_rls_policies():
    from app.main import generate_rls_policies
    state = {
        "project_id": "p1", "service_name": "PaymentService",
        "domain_entities": "", "openfga_model": "",
        "migrations": [], "rls_policies": [],
        "index_recommendations": [], "seed_scripts": [],
    }
    with patch("app.main.litellm.acompletion", new_callable=AsyncMock) as mock:
        mock.return_value = MagicMock(choices=[MagicMock(message=MagicMock(content="ALTER TABLE payments ENABLE ROW LEVEL SECURITY;"))])
        result = await generate_rls_policies(state)
    assert len(result["rls_policies"]) == 1
