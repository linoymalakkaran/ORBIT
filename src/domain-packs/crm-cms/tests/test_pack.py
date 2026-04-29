"""Tests for the CRM/CMS domain pack."""
from __future__ import annotations
import sys
from pathlib import Path
import pytest

sys.path.insert(0, str(Path(__file__).parent.parent))
from pack import get_domain_manifest, DOMAIN_NAME


def test_domain_name():
    assert DOMAIN_NAME == "crm-cms"


def test_manifest_has_required_keys():
    m = get_domain_manifest()
    for k in ("domain", "description", "compliance", "skills", "default_model", "data_classification"):
        assert k in m


def test_at_least_one_skill():
    assert len(get_domain_manifest()["skills"]) >= 1


def test_all_skills_have_id_and_name():
    for s in get_domain_manifest()["skills"]:
        assert "id" in s and "name" in s


def test_customer_360_skill_exists():
    ids = [s["id"] for s in get_domain_manifest()["skills"]]
    assert "crm-customer-360" in ids


def test_compliance_includes_pdpl():
    m = get_domain_manifest()
    assert "UAE-PDPL" in m["compliance"]
