"""JUL (Jebel Ali Port & Logistics) Domain Pack — port operations and logistics skills for ORBIT."""
from __future__ import annotations

import logging
from pathlib import Path
from typing import Any

import yaml

logger = logging.getLogger(__name__)

DOMAIN_NAME = "jul"
DOMAIN_DESCRIPTION = "Abu Dhabi Ports JUL — Jebel Ali port operations, vessel planning, and container logistics domain"

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
        "compliance": ["IMO-FAL", "WCO-SAFE", "UAE-Customs"],
        "skills": load_skills(),
        "default_model": "gpt-4o",
        "data_classification": "internal",
        "requires_pci_certification": False,
    }
