"""Tests for ticket implementation agent."""
import pytest
from unittest.mock import AsyncMock, patch, MagicMock


@pytest.mark.asyncio
async def test_analyse_ticket():
    from app.main import analyse_ticket
    state = {
        "project_id": "p1", "ticket_id": "ORBIT-123",
        "ticket_title": "Add payment method to user profile",
        "acceptance_criteria": [
            "User can add a credit card",
            "Card is validated via Luhn algorithm",
            "Card is stored in encrypted form",
        ],
        "openapi_stub": "", "service_name": "UserProfileService",
        "domain_entities_code": "", "cqrs_handlers_code": "",
        "migration_sql": "", "angular_component_code": "",
        "test_code": "", "branch_name": "", "pr_url": None,
        "pr_review": None, "implementation_notes": [],
    }
    with patch("app.main.litellm.acompletion", new_callable=AsyncMock) as mock:
        mock.return_value = MagicMock(choices=[MagicMock(message=MagicMock(
            content="1. Add PaymentMethod entity\n2. Add migration\n3. Add form component"
        ))])
        result = await analyse_ticket(state)
    assert len(result["implementation_notes"]) > 0
    assert "Implementation plan" in result["implementation_notes"][0]


@pytest.mark.asyncio
async def test_generate_migration():
    from app.main import generate_migration
    state = {
        "project_id": "p1", "ticket_id": "ORBIT-123",
        "ticket_title": "Add payment method storage",
        "acceptance_criteria": ["Store card token securely"],
        "openapi_stub": "", "service_name": "UserProfileService",
        "domain_entities_code": "", "cqrs_handlers_code": "",
        "migration_sql": "", "angular_component_code": "",
        "test_code": "", "branch_name": "", "pr_url": None,
        "pr_review": None, "implementation_notes": [],
    }
    with patch("app.main.litellm.acompletion", new_callable=AsyncMock) as mock:
        mock.return_value = MagicMock(choices=[MagicMock(message=MagicMock(
            content="CREATE TABLE payment_methods (id UUID PRIMARY KEY);"
        ))])
        result = await generate_migration(state)
    assert "migration_sql" in result
    assert len(result["migration_sql"]) > 0
