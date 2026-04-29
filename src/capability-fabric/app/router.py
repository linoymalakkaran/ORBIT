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


# ── G11: Skill Quality Scorer ────────────────────────────────────────────────

_REQUIRED_SKILL_FIELDS = ["name", "description", "category", "version", "instructions_key"]
_MIN_USE_CASES = 3

@router.get("/{skill_id}/score", response_model=dict)
async def score_skill(
    skill_id: uuid.UUID,
    _c: dict = Depends(require_auth),
    repo: SkillRepository = Depends(_repo),
) -> Any:
    """
    Phase 07 – G11: Computes a quality score (0–100) for a skill.
    Score = completeness (40%) × coverage (35%) × testability (25%)
    """
    skill = await repo.get_by_id(skill_id)
    if skill is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND)

    skill_dict = skill.model_dump() if hasattr(skill, "model_dump") else vars(skill)

    # ── Completeness: % of required fields that are present and non-empty ───
    filled = sum(
        1 for f in _REQUIRED_SKILL_FIELDS
        if skill_dict.get(f) not in (None, "", [], {})
    )
    completeness = filled / len(_REQUIRED_SKILL_FIELDS)

    # ── Coverage: use cases documented vs minimum 3 ──────────────────────────
    use_cases = skill_dict.get("use_cases") or []
    if isinstance(use_cases, str):
        use_cases = [u.strip() for u in use_cases.split(",") if u.strip()]
    coverage = min(len(use_cases), _MIN_USE_CASES) / _MIN_USE_CASES

    # ── Testability: examples + acceptance_criteria present ─────────────────
    has_examples            = bool(skill_dict.get("examples"))
    has_acceptance_criteria = bool(skill_dict.get("acceptance_criteria"))
    testability = (0.5 if has_examples else 0.0) + (0.5 if has_acceptance_criteria else 0.0)

    # ── Weighted score ────────────────────────────────────────────────────────
    score = round((completeness * 0.40 + coverage * 0.35 + testability * 0.25) * 100)
    grade = "A" if score >= 90 else "B" if score >= 75 else "C" if score >= 50 else "F"

    return {
        "skill_id": str(skill_id),
        "skill_name": skill_dict.get("name"),
        "score": score,
        "grade": grade,
        "breakdown": {
            "completeness": {
                "raw": round(completeness * 100),
                "weight": 0.40,
                "contribution": round(completeness * 40),
                "filled_fields": filled,
                "required_fields": len(_REQUIRED_SKILL_FIELDS),
            },
            "coverage": {
                "raw": round(coverage * 100),
                "weight": 0.35,
                "contribution": round(coverage * 35),
                "use_cases_count": len(use_cases),
                "minimum_expected": _MIN_USE_CASES,
            },
            "testability": {
                "raw": round(testability * 100),
                "weight": 0.25,
                "contribution": round(testability * 25),
                "has_examples": has_examples,
                "has_acceptance_criteria": has_acceptance_criteria,
            },
        },
    }
