"""ERP Domain Pack — enterprise resource planning skills for ORBIT."""
from __future__ import annotations

import logging
from pathlib import Path
from typing import Any

import yaml

logger = logging.getLogger(__name__)

DOMAIN_NAME = "erp"
DOMAIN_DESCRIPTION = "Abu Dhabi Ports ERP — finance, procurement, HR, and asset management domain"

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
        "compliance": ["IFRS", "UAE-FTA", "ISO-27001"],
        "skills": load_skills(),
        "default_model": "gpt-4o",
        "data_classification": "confidential",
        "requires_pci_certification": False,
    }
