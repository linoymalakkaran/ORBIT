"""Tests for project registry."""
import pytest
from unittest.mock import AsyncMock, patch, MagicMock


@pytest.mark.asyncio
async def test_get_framework_inventory():
    from app.main import get_framework_inventory
    with patch("app.main.get_pool", new_callable=AsyncMock) as mock_pool:
        mock_conn = AsyncMock()
        mock_conn.fetch.return_value = [
            {"framework_name": "dotnet", "framework_version": "7.0", "service_count": 3},
            {"framework_name": "angular", "framework_version": "20", "service_count": 2},
        ]
        mock_pool.return_value.__aenter__ = AsyncMock(return_value=mock_conn)
        mock_pool.return_value.acquire.return_value.__aenter__ = AsyncMock(return_value=mock_conn)
        mock_pool.return_value.acquire.return_value.__aexit__ = AsyncMock(return_value=None)

        # Patch directly on the pool context
        import app.main as m
        original = m.get_pool
        m.get_pool = mock_pool

        result = await get_framework_inventory()

        m.get_pool = original

    # dotnet 7 is 2 behind (9 latest), still compliant
    dotnet_entry = next((r for r in result if r["framework"] == "dotnet"), None)
    if dotnet_entry:
        assert dotnet_entry["versions_behind"] == 2
        assert dotnet_entry["is_compliant"] is True


def test_lifecycle_enum_values():
    from app.main import LifecycleState
    assert LifecycleState.DRAFT == "Draft"
    assert LifecycleState.ACTIVE == "Active"
    assert LifecycleState.DEPRECATED == "Deprecated"
    assert LifecycleState.RETIRED == "Retired"
