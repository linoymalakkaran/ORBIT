"""EventStoreDB writer — appends a new event and returns its stream/position."""
from __future__ import annotations

import json
import uuid
from typing import Any

from esdbclient import EventStoreDBClient, NewEvent, StreamState

from app.config import settings
from app.models import LedgerEventPayload


def _client() -> EventStoreDBClient:
    return EventStoreDBClient(uri=settings.esdb_connection_string)


def stream_name(project_id: uuid.UUID) -> str:
    return f"orbit-pipeline-{project_id}"


async def append_event(payload: LedgerEventPayload) -> tuple[str, int]:
    """Append event to EventStoreDB. Returns (stream_name, commit_position)."""
    event = NewEvent(
        id=uuid.uuid4(),
        type=payload.event_type,
        data=json.dumps(payload.model_dump(mode="json")).encode(),
    )
    stream = stream_name(payload.project_id)
    with _client() as client:
        result = client.append_to_stream(
            stream_name=stream,
            current_version=StreamState.ANY,
            events=[event],
        )
    return stream, result.commit_position
