"""Temporal.io workflow and activities for the ORBIT pipeline."""
from __future__ import annotations

import asyncio
from datetime import timedelta
from typing import Any

from temporalio import activity, workflow
from temporalio.client import Client
from temporalio.worker import Worker

from app.config import settings
from app.graph import PipelineState, build_graph


# ── Activities ────────────────────────────────────────────────────────────────

@activity.defn
async def run_pipeline_stage(state: dict) -> dict:
    """Execute one or more LangGraph pipeline stages until completion."""
    graph = build_graph().compile()
    ps = PipelineState(**state)
    final_state = await graph.ainvoke(ps)
    return dict(final_state)


@activity.defn
async def emit_ledger_event(project_id: str, event_type: str, stage: int) -> bool:
    """Write a ledger entry for the completed pipeline stage."""
    import httpx
    payload = {
        "event_type": event_type,
        "project_id": project_id,
        "stage_number": stage,
    }
    async with httpx.AsyncClient(timeout=10) as client:
        r = await client.post(f"{settings.ledger_api_url}/api/ledger", json=payload)
    return r.status_code == 201


# ── Workflow ──────────────────────────────────────────────────────────────────

@workflow.defn
class OrbitPipelineWorkflow:
    @workflow.run
    async def run(
        self,
        project_id: str,
        project_name: str,
        requirements: str,
        data_classification: str = "internal",
        task_sensitivity: str = "internal",
    ) -> dict:
        initial_state = {
            "project_id": project_id,
            "project_name": project_name,
            "requirements": requirements,
            "stage": 1,
            "messages": [],
            "artifacts": [],
            "errors": [],
            "completed": False,
            # G27: pass routing axes into the LangGraph state
            "data_classification": data_classification,
            "task_sensitivity": task_sensitivity,
        }

        result = await workflow.execute_activity(
            run_pipeline_stage,
            initial_state,
            schedule_to_close_timeout=timedelta(minutes=30),
        )

        await workflow.execute_activity(
            emit_ledger_event,
            args=[project_id, "pipeline.completed", 12],
            schedule_to_close_timeout=timedelta(seconds=30),
        )

        return result


# ── Worker startup ─────────────────────────────────────────────────────────────

async def start_worker():
    client = await Client.connect(settings.temporal_host, namespace=settings.temporal_namespace)
    worker = Worker(
        client,
        task_queue=settings.temporal_task_queue,
        workflows=[OrbitPipelineWorkflow],
        activities=[run_pipeline_stage, emit_ledger_event],
    )
    await worker.run()
