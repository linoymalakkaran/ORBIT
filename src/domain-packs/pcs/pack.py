"""PCS (Port Community System) Domain Pack — port community and trade facilitation skills for ORBIT."""
from __future__ import annotations

import logging
from pathlib import Path
from typing import Any

import yaml

logger = logging.getLogger(__name__)

DOMAIN_NAME = "pcs"
DOMAIN_DESCRIPTION = "Abu Dhabi Ports PCS — Port Community System: single-window trade facilitation, customs, and shipping line integration"

SKILLS_DIR = Path(__file__).parent / "skills"


def load_skills() -> list[dict[str, Any]]:
    skills = []
    for path in sorted(SKILLS_DIR.glob("*.yaml")):
        with path.open("r", encoding="utf-8") as f:
            skill = yaml.safe_load(f)
            skill["_source"] = path.name
            skills.append(skill)
    return skills


def get_domain_manifest() -> dict[str, Any]:
    return {
        "domain": DOMAIN_NAME,
        "description": DOMAIN_DESCRIPTION,
        "compliance": ["WCO-SAFE", "UAE-Customs", "IMO-FAL"],
        "skills": load_skills(),
        "default_model": "gpt-4o",
        "data_classification": "internal",
        "requires_pci_certification": False,
    }
