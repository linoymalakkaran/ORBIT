"""FastAPI routers for Capability Fabric (skills CRUD + instructions upload)."""
from __future__ import annotations

import io
import uuid
from typing import Any, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, UploadFile, status
from minio import Minio

from app.auth import require_auth
from app.config import settings
from app.models import SkillCreate, SkillSpec, SkillUpdate
from app.repository import SkillRepository

router = APIRouter(prefix="/api/skills", tags=["skills"])


def _repo() -> SkillRepository:
    from app.main import _repository
    return _repository


def _minio() -> Minio:
    return Minio(
        settings.minio_endpoint,
        access_key=settings.minio_access_key,
        secret_key=settings.minio_secret_key,
        secure=False,
    )


# ── CRUD ──────────────────────────────────────────────────────────────────────

@router.post("", status_code=status.HTTP_201_CREATED, response_model=SkillSpec)
async def create_skill(
    body: SkillCreate,
    _c: dict = Depends(require_auth),
    repo: SkillRepository = Depends(_repo),
) -> Any:
    existing = await repo.get_by_name(body.name)
    if existing:
        raise HTTPException(status.HTTP_409_CONFLICT, detail=f"Skill '{body.name}' already exists")
    return await repo.create_skill(body)


@router.get("", response_model=dict)
async def list_skills(
    category: Optional[str] = None,
    status_filter: Optional[str] = Query(None, alias="status"),
    page: int = Query(1, ge=1),
    size: int = Query(50, ge=1, le=200),
    _c: dict = Depends(require_auth),
    repo: SkillRepository = Depends(_repo),
) -> Any:
    items, total = await repo.list_skills(category, status_filter, page, size)
    return {"items": items, "total": total, "page": page, "size": size}


@router.get("/{skill_id}", response_model=SkillSpec)
async def get_skill(
    skill_id: uuid.UUID,
    _c: dict = Depends(require_auth),
    repo: SkillRepository = Depends(_repo),
) -> Any:
    skill = await repo.get_by_id(skill_id)
    if skill is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND)
    return skill


@router.put("/{skill_id}", response_model=SkillSpec)
async def update_skill(
    skill_id: uuid.UUID,
    body: SkillUpdate,
    _c: dict = Depends(require_auth),
    repo: SkillRepository = Depends(_repo),
) -> Any:
    updated = await repo.update_skill(skill_id, body)
    if updated is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND)
    return updated


@router.delete("/{skill_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_skill(
    skill_id: uuid.UUID,
    _c: dict = Depends(require_auth),
    repo: SkillRepository = Depends(_repo),
) -> None:
    deleted = await repo.delete_skill(skill_id)
    if not deleted:
        raise HTTPException(status.HTTP_404_NOT_FOUND)


# ── Instructions upload (MinIO) ───────────────────────────────────────────────

@router.post("/{skill_id}/instructions", response_model=dict)
async def upload_instructions(
    skill_id: uuid.UUID,
    file: UploadFile,
    _c: dict = Depends(require_auth),
    repo: SkillRepository = Depends(_repo),
) -> Any:
    skill = await repo.get_by_id(skill_id)
    if skill is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND)

    content = await file.read()
    key = f"instructions/{skill_id}/{file.filename}"
    mc = _minio()
    mc.put_object(
        settings.minio_bucket_skills,
        key,
        io.BytesIO(content),
        length=len(content),
        content_type="text/markdown",
    )
    await repo.update_skill(skill_id, SkillUpdate(instructions_key=key))
    return {"object_key": key, "size": len(content)}


@router.get("/{skill_id}/instructions")
async def get_instructions(
    skill_id: uuid.UUID,
    _c: dict = Depends(require_auth),
    repo: SkillRepository = Depends(_repo),
) -> Any:
    skill = await repo.get_by_id(skill_id)
    if skill is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND)
    mc = _minio()
    try:
        response = mc.get_object(settings.minio_bucket_skills, skill.instructions_key)
        content = response.read().decode("utf-8")
    except Exception as exc:
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail="Instructions not found") from exc
    return {"content": content}
