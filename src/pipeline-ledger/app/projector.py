"""Kafka consumer that projects EventStoreDB events into the Postgres read model."""
from __future__ import annotations

import asyncio
import json
import logging
import uuid
from datetime import datetime, timezone

from confluent_kafka import Consumer, KafkaError, KafkaException

from app.config import settings
from app.models import LedgerEntry, LedgerEventPayload
from app.repository import LedgerRepository

logger = logging.getLogger(__name__)


def _make_consumer() -> Consumer:
    return Consumer(
        {
            "bootstrap.servers": settings.kafka_bootstrap_servers,
            "group.id": settings.kafka_consumer_group,
            "auto.offset.reset": "earliest",
            "enable.auto.commit": False,
        }
    )


async def run_projector(repo: LedgerRepository) -> None:
    """Long-running Kafka consumer loop. Runs in background task."""
    consumer = _make_consumer()
    consumer.subscribe([settings.kafka_topic_events])
    logger.info("Ledger projector started, topic=%s", settings.kafka_topic_events)

    try:
        while True:
            msg = consumer.poll(timeout=1.0)
            if msg is None:
                await asyncio.sleep(0.01)
                continue
            if msg.error():
                if msg.error().code() == KafkaError._PARTITION_EOF:
                    continue
                raise KafkaException(msg.error())

            try:
                data = json.loads(msg.value())
                payload = LedgerEventPayload.model_validate(data)
                entry = await _project(repo, payload, msg.offset())
                logger.info("Projected event %s pos=%d hash=%s", entry.event_type, entry.esdb_position, entry.entry_hash[:8])
                consumer.commit(message=msg, asynchronous=False)
            except Exception:
                logger.exception("Failed to project event, skipping offset %d", msg.offset())
    finally:
        consumer.close()


async def _project(repo: LedgerRepository, payload: LedgerEventPayload, offset: int) -> LedgerEntry:
    prev = await repo.get_latest(payload.project_id)
    prev_hash = prev.entry_hash if prev else ""

    entry = LedgerEntry(
        id=uuid.uuid4(),
        project_id=payload.project_id,
        event_type=payload.event_type,
        stage_number=payload.stage_number,
        actor_id=payload.actor_id,
        metadata=payload.metadata,
        occurred_at=payload.occurred_at,
        esdb_stream=f"orbit-pipeline-{payload.project_id}",
        esdb_position=offset,
        prev_hash=prev_hash,
    )
    entry.entry_hash = entry.compute_hash()
    await repo.save(entry)
    return entry
