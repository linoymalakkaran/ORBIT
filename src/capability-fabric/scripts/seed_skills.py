"""Seed all skill YAML files from skills/ directory into the Capability Fabric API."""
from __future__ import annotations

import os
import sys
import httpx
import yaml
from pathlib import Path

API_BASE = os.environ.get("FABRIC_API_URL", "http://localhost:8001")
TOKEN    = os.environ.get("FABRIC_TOKEN", "")

headers = {"Authorization": f"Bearer {TOKEN}", "Content-Type": "application/json"}
skills_dir = Path(__file__).parent / "skills"


def main():
    for yml in sorted(skills_dir.glob("*.yaml")):
        data = yaml.safe_load(yml.read_text())
        resp = httpx.post(f"{API_BASE}/api/skills", json=data, headers=headers, timeout=10)
        if resp.status_code in (200, 201):
            print(f"  CREATED  {data['name']}")
        elif resp.status_code == 409:
            print(f"  EXISTS   {data['name']}")
        else:
            print(f"  ERROR    {data['name']} → {resp.status_code}: {resp.text}", file=sys.stderr)


if __name__ == "__main__":
    main()
