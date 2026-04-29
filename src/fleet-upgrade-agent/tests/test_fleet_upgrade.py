"""Tests for Fleet Upgrade Agent — Phase 24."""
from __future__ import annotations

import pytest
from app.main import (
    LATEST_VERSIONS,
    _calculate_lag,
    _parse_major,
)


def test_parse_major_dotnet():
    assert _parse_major("9.0") == 9


def test_parse_major_angular():
    assert _parse_major("20.3.1") == 20


def test_parse_major_invalid():
    assert _parse_major("invalid") == 0


def test_calculate_lag_same_version():
    assert _calculate_lag("20.0", "20.0") == 0


def test_calculate_lag_one_behind():
    assert _calculate_lag("19.0", "20.0") == 1


def test_calculate_lag_two_behind():
    assert _calculate_lag("8.0", "10.0") == 2


def test_calculate_lag_ahead():
    # current > latest → 0 lag (no negative lag)
    assert _calculate_lag("21.0", "20.0") == 0


def test_latest_versions_defined():
    assert "angular" in LATEST_VERSIONS
    assert "dotnet" in LATEST_VERSIONS
    assert "nodejs" in LATEST_VERSIONS
    assert "python" in LATEST_VERSIONS


def test_dotnet_latest_is_nine():
    assert _parse_major(LATEST_VERSIONS["dotnet"]) == 9


def test_angular_latest_is_twenty():
    assert _parse_major(LATEST_VERSIONS["angular"]) == 20


def test_nodejs_latest_is_twentytwo():
    assert _parse_major(LATEST_VERSIONS["nodejs"]) == 22
