"""FastAPI router for the Orchestrator API."""
from __future__ import annotations

import uuid
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from temporalio.client import Client

from app.auth import require_auth
from app.config import settings
from app.temporal_worker import OrbitPipelineWorkflow

router = APIRouter(prefix="/api/pipelines", tags=["pipelines"])


class PipelineStartRequest(BaseModel):
    project_id: uuid.UUID
    project_name: str
    requirements: str
    # G27: intelligent routing axes — defaults match Settings defaults
    data_classification: str = "internal"   # public | internal | confidential | restricted
    task_sensitivity: str = "internal"      # public | internal | confidential | restricted


async def _temporal_client() -> Client:
    return await Client.connect(settings.temporal_host, namespace=settings.temporal_namespace)


@router.post("", status_code=status.HTTP_202_ACCEPTED)
async def start_pipeline(
    body: PipelineStartRequest,
    _claims: dict = Depends(require_auth),
) -> Any:
    client = await _temporal_client()
    workflow_id = f"pipeline-{body.project_id}"
    handle = await client.start_workflow(
        OrbitPipelineWorkflow.run,
        args=[
            str(body.project_id),
            body.project_name,
            body.requirements,
            body.data_classification,
            body.task_sensitivity,
        ],
        id=workflow_id,
        task_queue=settings.temporal_task_queue,
    )
    return {"workflow_id": handle.id, "run_id": handle.result_run_id}


@router.get("/{workflow_id}/status")
async def get_pipeline_status(
    workflow_id: str,
    _claims: dict = Depends(require_auth),
) -> Any:
    client = await _temporal_client()
    handle = client.get_workflow_handle(workflow_id)
    desc = await handle.describe()
    return {
        "workflow_id": workflow_id,
        "status": str(desc.status),
        "start_time": desc.start_time.isoformat() if desc.start_time else None,
    }


@router.post("/{workflow_id}/cancel", status_code=status.HTTP_204_NO_CONTENT)
async def cancel_pipeline(
    workflow_id: str,
    _claims: dict = Depends(require_auth),
) -> None:
    client = await _temporal_client()
    handle = client.get_workflow_handle(workflow_id)
    await handle.cancel()
