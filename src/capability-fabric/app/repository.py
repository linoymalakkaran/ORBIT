from __future__ import annotations

import uuid
from datetime import datetime, timezone
from typing import Optional

from sqlalchemy import select, func, update as sa_update
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.config import settings
from app.db import Base, SkillORM
from app.models import SkillCreate, SkillSpec, SkillUpdate


class SkillRepository:
    def __init__(self, session_factory: async_sessionmaker[AsyncSession]):
        self._sf = session_factory

    @classmethod
    def create(cls) -> "SkillRepository":
        engine = create_async_engine(settings.pg_dsn, pool_size=5, max_overflow=10)
        factory = async_sessionmaker(engine, expire_on_commit=False)
        return cls(factory)

    async def migrate(self):
        engine = create_async_engine(settings.pg_dsn)
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)

    async def create_skill(self, data: SkillCreate) -> SkillSpec:
        now = datetime.now(timezone.utc)
        orm = SkillORM(
            id=uuid.uuid4(),
            name=data.name,
            display_name=data.display_name,
            version=data.version,
            category=data.category,
            status="active",
            description=data.description,
            instructions_key=data.instructions_key,
            parameters=[p.model_dump() for p in data.parameters],
            tags=data.tags,
            mcp_servers=data.mcp_servers,
            created_at=now,
            updated_at=now,
        )
        async with self._sf() as session:
            session.add(orm)
            await session.commit()
            await session.refresh(orm)
        return _to_model(orm)

    async def get_by_id(self, skill_id: uuid.UUID) -> Optional[SkillSpec]:
        async with self._sf() as session:
            row = await session.get(SkillORM, skill_id)
        return _to_model(row) if row else None

    async def get_by_name(self, name: str) -> Optional[SkillSpec]:
        async with self._sf() as session:
            stmt = select(SkillORM).where(SkillORM.name == name)
            row = (await session.execute(stmt)).scalar_one_or_none()
        return _to_model(row) if row else None

    async def list_skills(
        self,
        category: Optional[str] = None,
        status: Optional[str] = None,
        page: int = 1,
        size: int = 50,
    ) -> tuple[list[SkillSpec], int]:
        async with self._sf() as session:
            stmt = select(SkillORM)
            count_stmt = select(func.count(SkillORM.id))
            if category:
                stmt = stmt.where(SkillORM.category == category)
                count_stmt = count_stmt.where(SkillORM.category == category)
            if status:
                stmt = stmt.where(SkillORM.status == status)
                count_stmt = count_stmt.where(SkillORM.status == status)
            stmt = stmt.offset((page - 1) * size).limit(size)
            rows = (await session.execute(stmt)).scalars().all()
            total = (await session.execute(count_stmt)).scalar_one()
        return [_to_model(r) for r in rows], total

    async def update_skill(self, skill_id: uuid.UUID, data: SkillUpdate) -> Optional[SkillSpec]:
        updates = data.model_dump(exclude_none=True)
        if not updates:
            return await self.get_by_id(skill_id)
        updates["updated_at"] = datetime.now(timezone.utc)
        if "parameters" in updates:
            updates["parameters"] = [p if isinstance(p, dict) else p.model_dump() for p in updates["parameters"]]
        async with self._sf() as session:
            await session.execute(
                sa_update(SkillORM).where(SkillORM.id == skill_id).values(**updates)
            )
            await session.commit()
        return await self.get_by_id(skill_id)

    async def delete_skill(self, skill_id: uuid.UUID) -> bool:
        async with self._sf() as session:
            row = await session.get(SkillORM, skill_id)
            if row is None:
                return False
            await session.delete(row)
            await session.commit()
        return True


def _to_model(o: SkillORM) -> SkillSpec:
    from app.models import SkillParameter
    return SkillSpec(
        id=o.id,
        name=o.name,
        display_name=o.display_name,
        version=o.version,
        category=o.category,  # type: ignore[arg-type]
        status=o.status,      # type: ignore[arg-type]
        description=o.description,
        instructions_key=o.instructions_key,
        parameters=[SkillParameter(**p) for p in (o.parameters or [])],
        tags=list(o.tags or []),
        mcp_servers=list(o.mcp_servers or []),
        created_at=o.created_at,
        updated_at=o.updated_at,
    )
