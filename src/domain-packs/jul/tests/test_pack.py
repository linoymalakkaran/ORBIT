"""Tests for the JUL (Jebel Ali Port & Logistics) domain pack."""
from __future__ import annotations
import sys
from pathlib import Path
import pytest

sys.path.insert(0, str(Path(__file__).parent.parent))
from pack import get_domain_manifest, DOMAIN_NAME


def test_domain_name():
    assert DOMAIN_NAME == "jul"


def test_manifest_has_required_keys():
    m = get_domain_manifest()
    for k in ("domain", "description", "compliance", "skills", "default_model", "data_classification"):
        assert k in m


def test_at_least_one_skill():
    assert len(get_domain_manifest()["skills"]) >= 1


def test_all_skills_have_id_and_name():
    for s in get_domain_manifest()["skills"]:
        assert "id" in s and "name" in s


def test_vessel_planning_skill_exists():
    ids = [s["id"] for s in get_domain_manifest()["skills"]]
    assert "jul-vessel-planning" in ids


def test_compliance_includes_imo():
    m = get_domain_manifest()
    assert any("IMO" in c for c in m["compliance"])


def test_data_classification_internal():
    assert get_domain_manifest()["data_classification"] == "internal"
