"""Tests for the MPay domain pack — validates skill definitions and domain manifest."""
from __future__ import annotations

import sys
from pathlib import Path

import pytest
import yaml

# Allow running tests from repo root
sys.path.insert(0, str(Path(__file__).parent.parent))
from pack import get_domain_manifest, DOMAIN_NAME


def test_domain_name():
    assert DOMAIN_NAME == "mpay"


def test_manifest_has_required_keys():
    manifest = get_domain_manifest()
    for key in ("domain", "description", "compliance", "skills", "default_model", "data_classification"):
        assert key in manifest, f"Missing key: {key}"


def test_manifest_data_classification_restricted():
    manifest = get_domain_manifest()
    assert manifest["data_classification"] == "restricted"


def test_manifest_requires_pci():
    manifest = get_domain_manifest()
    assert manifest.get("requires_pci_certification") is True


def test_at_least_one_skill():
    manifest = get_domain_manifest()
    assert len(manifest["skills"]) >= 1, "Domain pack must have at least one skill"


def test_all_skills_have_id_and_name():
    manifest = get_domain_manifest()
    for skill in manifest["skills"]:
        assert "id" in skill, f"Skill missing 'id': {skill}"
        assert "name" in skill, f"Skill missing 'name': {skill}"


def test_all_skills_have_data_classification_restricted():
    manifest = get_domain_manifest()
    for skill in manifest["skills"]:
        assert skill.get("data_classification") == "restricted", \
            f"MPay skill '{skill.get('id')}' must be classified 'restricted'"


def test_payment_initiation_skill_exists():
    manifest = get_domain_manifest()
    ids = [s["id"] for s in manifest["skills"]]
    assert "mpay-payment-initiation" in ids


def test_skills_have_no_pan_in_logs_control():
    manifest = get_domain_manifest()
    for skill in manifest["skills"]:
        controls = skill.get("security_controls", {})
        if isinstance(controls, list):
            # List of dicts — check any entry has no_pan_in_logs
            has_control = any(
                (isinstance(c, dict) and c.get("no_pan_in_logs")) for c in controls
            )
        elif isinstance(controls, dict):
            has_control = controls.get("no_pan_in_logs", False)
        else:
            has_control = False
        # Only enforce for payment-touching skills
        if "payment" in skill.get("id", ""):
            assert has_control, f"Payment skill '{skill['id']}' must have no_pan_in_logs control"
