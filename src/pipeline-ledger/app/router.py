"""FastAPI routers for the Pipeline Ledger service."""
from __future__ import annotations

import uuid
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Query, status

from app.auth import require_auth
from app.esdb_writer import append_event
from app.models import ChainVerificationResult, LedgerEntry, LedgerEventPayload
from app.repository import LedgerRepository

router = APIRouter(prefix="/api/ledger", tags=["ledger"])


def _repo(request=None) -> LedgerRepository:
    from app.main import _repository  # lazy import to avoid circular
    return _repository


# ── Write ──────────────────────────────────────────────────────────────────────

@router.post("", status_code=status.HTTP_201_CREATED, response_model=LedgerEntry)
async def append(
    payload: LedgerEventPayload,
    _claims: dict = Depends(require_auth),
    repo: LedgerRepository = Depends(_repo),
) -> Any:
    stream, position = await append_event(payload)
    prev = await repo.get_latest(payload.project_id)
    prev_hash = prev.entry_hash if prev else ""
    entry = LedgerEntry(
        project_id=payload.project_id,
        event_type=payload.event_type,
        stage_number=payload.stage_number,
        actor_id=payload.actor_id,
        metadata=payload.metadata,
        occurred_at=payload.occurred_at,
        esdb_stream=stream,
        esdb_position=position,
        prev_hash=prev_hash,
    )
    entry.entry_hash = entry.compute_hash()
    await repo.save(entry)
    return entry


# ── Read ───────────────────────────────────────────────────────────────────────

@router.get("", response_model=dict)
async def list_entries(
    projectId: uuid.UUID = Query(..., alias="projectId"),
    page: int = Query(1, ge=1),
    size: int = Query(50, ge=1, le=200),
    _claims: dict = Depends(require_auth),
    repo: LedgerRepository = Depends(_repo),
) -> Any:
    items, total = await repo.list_by_project(projectId, page, size)
    return {"items": items, "total": total, "page": page, "size": size}


@router.get("/verify", response_model=ChainVerificationResult)
async def verify_chain(
    projectId: uuid.UUID = Query(..., alias="projectId"),
    _claims: dict = Depends(require_auth),
    repo: LedgerRepository = Depends(_repo),
) -> Any:
    return await repo.verify_chain(projectId)


# ── Compliance export ──────────────────────────────────────────────────────────

@router.get("/export/{project_id}")
async def export_compliance(
    project_id: uuid.UUID,
    _claims: dict = Depends(require_auth),
    repo: LedgerRepository = Depends(_repo),
) -> Any:
    items, _ = await repo.list_by_project(project_id, page=1, size=10_000)
    return {
        "project_id": str(project_id),
        "entry_count": len(items),
        "entries": [e.model_dump(mode="json") for e in items],
    }
