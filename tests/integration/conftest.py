"""Integration test configuration and shared fixtures."""
import pytest


def pytest_configure(config):
    """Configure pytest-asyncio mode."""
    config.addinivalue_line(
        "markers", "asyncio: mark test as asyncio coroutine"
    )
