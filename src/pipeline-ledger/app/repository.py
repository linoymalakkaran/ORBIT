"""Postgres async repository for LedgerEntry read-model."""
from __future__ import annotations

import uuid
from typing import Optional

from sqlalchemy import select, func, and_
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.config import settings
from app.db import Base, LedgerEntryORM
from app.models import ChainVerificationResult, LedgerEntry


def _make_engine():
    return create_async_engine(settings.pg_dsn, pool_size=5, max_overflow=10)


class LedgerRepository:
    def __init__(self, session_factory: async_sessionmaker[AsyncSession]):
        self._sf = session_factory

    @classmethod
    def create(cls) -> "LedgerRepository":
        engine = _make_engine()
        factory = async_sessionmaker(engine, expire_on_commit=False)
        return cls(factory)

    async def migrate(self):
        engine = _make_engine()
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)

    async def save(self, entry: LedgerEntry) -> None:
        async with self._sf() as session:
            orm = LedgerEntryORM(
                id=entry.id,
                project_id=entry.project_id,
                event_type=entry.event_type,
                stage_number=entry.stage_number,
                actor_id=entry.actor_id,
                metadata=entry.metadata,
                occurred_at=entry.occurred_at,
                esdb_stream=entry.esdb_stream,
                esdb_position=entry.esdb_position,
                entry_hash=entry.entry_hash,
                prev_hash=entry.prev_hash,
            )
            session.add(orm)
            await session.commit()

    async def get_latest(self, project_id: uuid.UUID) -> Optional[LedgerEntry]:
        async with self._sf() as session:
            stmt = (
                select(LedgerEntryORM)
                .where(LedgerEntryORM.project_id == project_id)
                .order_by(LedgerEntryORM.esdb_position.desc())
                .limit(1)
            )
            result = await session.execute(stmt)
            orm = result.scalar_one_or_none()
        if orm is None:
            return None
        return _orm_to_model(orm)

    async def list_by_project(
        self, project_id: uuid.UUID, page: int = 1, size: int = 50
    ) -> tuple[list[LedgerEntry], int]:
        async with self._sf() as session:
            stmt = (
                select(LedgerEntryORM)
                .where(LedgerEntryORM.project_id == project_id)
                .order_by(LedgerEntryORM.occurred_at.asc())
                .offset((page - 1) * size)
                .limit(size)
            )
            count_stmt = select(func.count()).where(LedgerEntryORM.project_id == project_id)
            rows = (await session.execute(stmt)).scalars().all()
            total = (await session.execute(count_stmt)).scalar_one()
        return [_orm_to_model(r) for r in rows], total

    async def verify_chain(self, project_id: uuid.UUID) -> ChainVerificationResult:
        async with self._sf() as session:
            stmt = (
                select(LedgerEntryORM)
                .where(LedgerEntryORM.project_id == project_id)
                .order_by(LedgerEntryORM.esdb_position.asc())
            )
            rows = (await session.execute(stmt)).scalars().all()

        checked = 0
        prev_hash = ""
        for row in rows:
            entry = _orm_to_model(row)
            if entry.prev_hash != prev_hash:
                return ChainVerificationResult(valid=False, checked=checked, failed_at_event_id=entry.id)
            expected = entry.compute_hash()
            if expected != entry.entry_hash:
                return ChainVerificationResult(valid=False, checked=checked, failed_at_event_id=entry.id)
            prev_hash = entry.entry_hash
            checked += 1

        return ChainVerificationResult(valid=True, checked=checked)


def _orm_to_model(o: LedgerEntryORM) -> LedgerEntry:
    return LedgerEntry(
        id=o.id,
        project_id=o.project_id,
        event_type=o.event_type,
        stage_number=o.stage_number,
        actor_id=o.actor_id,
        metadata=o.metadata or {},
        occurred_at=o.occurred_at,
        esdb_stream=o.esdb_stream,
        esdb_position=o.esdb_position,
        entry_hash=o.entry_hash,
        prev_hash=o.prev_hash,
    )
