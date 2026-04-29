"""Tests for architecture proposal agent."""
import pytest
import asyncio
from unittest.mock import AsyncMock, patch, MagicMock


@pytest.mark.asyncio
async def test_extract_intent_node():
    from app.main import extract_intent
    state = {
        "project_id": "test-001",
        "brd_text": "Build a payment gateway microservice with Visa and Mastercard support.",
        "intent": "",
        "bounded_contexts": [],
        "services": [],
        "openapi_stubs": [],
        "drawio_component_xml": "",
        "drawio_sequence_xml": "",
        "infra_plan": "",
        "qa_plan": "",
        "security_plan": "",
        "proposal_version": 1,
    }
    with patch("app.main.litellm.acompletion", new_callable=AsyncMock) as mock_llm:
        mock_llm.return_value = MagicMock(choices=[MagicMock(message=MagicMock(content="Payment gateway with Visa/Mastercard."))])
        result = await extract_intent(state)
    assert "intent" in result
    assert len(result["intent"]) > 0


@pytest.mark.asyncio
async def test_decompose_bounded_contexts():
    from app.main import decompose_bounded_contexts
    state = {
        "project_id": "test-001",
        "brd_text": "Payment gateway system.",
        "intent": "A payment gateway supporting multiple card schemes.",
        "bounded_contexts": [],
        "services": [],
        "openapi_stubs": [],
        "drawio_component_xml": "",
        "drawio_sequence_xml": "",
        "infra_plan": "",
        "qa_plan": "",
        "security_plan": "",
        "proposal_version": 1,
    }
    with patch("app.main.litellm.acompletion", new_callable=AsyncMock) as mock_llm:
        mock_llm.return_value = MagicMock(choices=[MagicMock(message=MagicMock(content='[{"name": "Payments", "responsibility": "Process transactions", "interfaces": ["REST"]}]'))])
        result = await decompose_bounded_contexts(state)
    assert len(result["bounded_contexts"]) > 0
    assert len(result["services"]) > 0
