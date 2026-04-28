from __future__ import annotations

import hashlib
import json
import uuid
from datetime import datetime, timezone
from typing import Optional

from pydantic import BaseModel, Field


def _now_utc() -> datetime:
    return datetime.now(timezone.utc)


class LedgerEventPayload(BaseModel):
    """Incoming event payload written to EventStoreDB."""

    event_type: str
    project_id: uuid.UUID
    stage_number: Optional[int] = None
    actor_id: Optional[uuid.UUID] = None
    metadata: dict = Field(default_factory=dict)
    occurred_at: datetime = Field(default_factory=_now_utc)


class LedgerEntry(BaseModel):
    """Projection stored in Postgres for fast querying."""

    id: uuid.UUID = Field(default_factory=uuid.uuid4)
    project_id: uuid.UUID
    event_type: str
    stage_number: Optional[int] = None
    actor_id: Optional[uuid.UUID] = None
    metadata: dict = Field(default_factory=dict)
    occurred_at: datetime = Field(default_factory=_now_utc)
    esdb_stream: str = ""
    esdb_position: int = 0
    entry_hash: str = ""
    prev_hash: str = ""

    def compute_hash(self) -> str:
        """SHA-256 of canonical JSON of this entry (excluding entry_hash field)."""
        payload = {
            "id": str(self.id),
            "project_id": str(self.project_id),
            "event_type": self.event_type,
            "stage_number": self.stage_number,
            "actor_id": str(self.actor_id) if self.actor_id else None,
            "occurred_at": self.occurred_at.isoformat(),
            "prev_hash": self.prev_hash,
        }
        canonical = json.dumps(payload, sort_keys=True, separators=(",", ":"))
        return hashlib.sha256(canonical.encode()).hexdigest()


class ChainVerificationResult(BaseModel):
    valid: bool
    checked: int
    failed_at_event_id: Optional[uuid.UUID] = None
    error: Optional[str] = None
