from __future__ import annotations

import uuid
from datetime import datetime, timezone
from typing import Literal, Optional

from pydantic import BaseModel, Field


SkillCategory = Literal[
    "analysis", "generation", "review", "testing",
    "deployment", "security", "documentation", "orchestration"
]

SkillStatus = Literal["draft", "active", "deprecated"]


class SkillParameter(BaseModel):
    name: str
    type: str          # e.g. "string", "integer", "boolean"
    description: str
    required: bool = True
    default: Optional[str] = None


class SkillSpec(BaseModel):
    """Full skill specification (YAML-serialisable)."""

    id: uuid.UUID = Field(default_factory=uuid.uuid4)
    name: str                        # e.g. "code_review"
    display_name: str
    version: str = "1.0.0"
    category: SkillCategory
    status: SkillStatus = "active"
    description: str
    instructions_key: str            # MinIO object key for the system prompt
    parameters: list[SkillParameter] = Field(default_factory=list)
    tags: list[str] = Field(default_factory=list)
    mcp_servers: list[str] = Field(default_factory=list)  # required MCP server ids
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


class SkillCreate(BaseModel):
    name: str
    display_name: str
    version: str = "1.0.0"
    category: SkillCategory
    description: str
    instructions_key: str
    parameters: list[SkillParameter] = Field(default_factory=list)
    tags: list[str] = Field(default_factory=list)
    mcp_servers: list[str] = Field(default_factory=list)


class SkillUpdate(BaseModel):
    display_name: Optional[str] = None
    description: Optional[str] = None
    status: Optional[SkillStatus] = None
    instructions_key: Optional[str] = None
    parameters: Optional[list[SkillParameter]] = None
    tags: Optional[list[str]] = None
    mcp_servers: Optional[list[str]] = None
    version: Optional[str] = None
