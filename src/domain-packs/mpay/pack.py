"""MPay Domain Pack — PCI-DSS compliant payment processing skills for ORBIT."""
from __future__ import annotations

import logging
from pathlib import Path
from typing import Any

import yaml

logger = logging.getLogger(__name__)

DOMAIN_NAME = "mpay"
DOMAIN_DESCRIPTION = "Abu Dhabi Ports MPay — PCI-DSS v4.0 compliant payment processing domain"

SKILLS_DIR = Path(__file__).parent / "skills"


def load_skills() -> list[dict[str, Any]]:
    """Load all skill definitions from the skills/ directory."""
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
        "compliance": ["PCI-DSS-v4.0", "UAE-CBUAE"],
        "skills": load_skills(),
        "default_model": "gpt-4o",            # PCI scope — no sovereign routing
        "data_classification": "restricted",
        "requires_pci_certification": True,
    }
