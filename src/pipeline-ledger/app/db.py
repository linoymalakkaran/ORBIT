"""SQLAlchemy async ORM definitions for the ledger read model (PostgreSQL)."""
from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import UUID, BigInteger, DateTime, Integer, String, Text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


class Base(DeclarativeBase):
    pass


class LedgerEntryORM(Base):
    __tablename__ = "ledger_entries"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True)
    project_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), index=True, nullable=False)
    event_type: Mapped[str] = mapped_column(String(120), nullable=False)
    stage_number: Mapped[int | None] = mapped_column(Integer, nullable=True)
    actor_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), nullable=True)
    metadata: Mapped[dict] = mapped_column(JSONB, nullable=False, default={})
    occurred_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, index=True)
    esdb_stream: Mapped[str] = mapped_column(String(256), nullable=False, default="")
    esdb_position: Mapped[int] = mapped_column(BigInteger, nullable=False, default=0)
    entry_hash: Mapped[str] = mapped_column(String(64), nullable=False, default="")
    prev_hash: Mapped[str] = mapped_column(String(64), nullable=False, default="")
