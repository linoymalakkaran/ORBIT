# Skill: Temporal.io Workflow Scaffold

## Skill ID
`temporal-workflow-scaffold`

## Version
`1.0.0`

## Used By
- Phase 10 (Orchestration Agent — durable workflow wrapper)
- Phase 24 (Fleet Upgrade Campaign — long-running parallel campaigns)
- Phase 22 (Ticket Implementation Agent — multi-agent delegation flow)
- Any agent that executes operations spanning > 60 seconds or requiring retry durability

## Description
Standard pattern for implementing durable, fault-tolerant workflows using Temporal.io in the AD Ports AI Portal. Covers workflow definition, activity registration, retry policies, signal/query handlers, child workflows, and AKS deployment. Use Temporal when the orchestration step: (a) runs longer than 5 minutes, (b) must survive worker restarts, (c) requires human-in-the-loop pausing, or (d) coordinates parallel sub-tasks.

---

## Decision Guide: LangGraph vs Temporal

| Concern | LangGraph Only | Temporal (wrapping LangGraph) |
|---------|----------------|-------------------------------|
| Duration | < 5 minutes | > 5 minutes or fleet campaigns |
| Durability | In-memory (lost on restart) | Durable — survives restarts |
| Parallel execution | `asyncio.gather` | Temporal child workflows |
| Human approval pause | Polling loop | Temporal signal (event-driven) |
| Retry with backoff | Manual | Built-in retry policies |
| Fleet campaigns (10–100 services) | Not suitable | Use Temporal |

---

## Skill Inputs

```json
{
  "workflowName": "string",         // e.g. "fleet_upgrade_campaign"
  "workflowDisplayName": "string",
  "taskQueue": "string",            // e.g. "ai-portal-fleet"
  "inputSchema": { ... },           // Pydantic model for workflow input
  "outputSchema": { ... },          // Pydantic model for workflow result
  "activities": [
    {
      "name": "string",
      "description": "string",
      "timeout": "string",          // e.g. "30m", "2h"
      "retries": 3
    }
  ],
  "humanApprovalGate": false,       // Whether to add signal-based approval step
  "parallelismSemaphore": 5         // Max concurrent sub-workflows (0 = unlimited)
}
```

---

## Output Artefacts

```
agents/temporal/
├── workflows/
│   └── {workflow_name}.py          ← Temporal workflow definition
├── activities/
│   └── {workflow_name}_activities.py  ← Activity implementations
├── worker.py                       ← Temporal worker process
└── client.py                       ← Workflow starter (used by API / orchestrator)
```

---

## Workflow Definition Pattern

```python
# agents/temporal/workflows/{workflow_name}.py
from datetime import timedelta
from temporalio import workflow
from temporalio.common import RetryPolicy
import asyncio

from ..activities.{workflow_name}_activities import (
    {WorkflowName}Input,
    {WorkflowName}Result,
    prepare_activity,
    process_item_activity,
    verify_results_activity,
    notify_completion_activity,
)


@workflow.defn(name="{workflow_name}")
class {WorkflowName}Workflow:
    """
    {WorkflowDisplayName} — Temporal durable workflow.
    
    This workflow is idempotent. Re-running with the same workflow_id
    returns the existing result without re-executing completed activities.
    """

    def __init__(self) -> None:
        self._approval_received = False
        self._approval_decision: str | None = None
        self._cancelled = False

    @workflow.signal
    async def approve(self, decision: str) -> None:
        """Signal sent by Portal UI when human approves the workflow."""
        self._approval_received = True
        self._approval_decision = decision

    @workflow.signal
    async def cancel(self) -> None:
        """Signal sent by Portal UI to cancel the workflow gracefully."""
        self._cancelled = True

    @workflow.query
    def status(self) -> dict:
        """Query called by Portal UI to get real-time workflow status."""
        return {
            "approval_received": self._approval_received,
            "cancelled": self._cancelled,
        }

    @workflow.run
    async def run(self, input_data: {WorkflowName}Input) -> {WorkflowName}Result:
        workflow.logger.info(
            "Starting %s for project=%s",
            "{workflow_name}", input_data.project_id
        )

        # Phase 1: Preparation (deterministic, always retried on failure)
        prepared = await workflow.execute_activity(
            prepare_activity,
            input_data,
            schedule_to_close_timeout=timedelta(minutes=10),
            retry_policy=STANDARD_RETRY_POLICY,
        )

        # Phase 2: Human approval gate (optional)
        if input_data.require_approval:
            await self._wait_for_approval(input_data.approval_timeout_hours)
            if self._cancelled:
                return {WorkflowName}Result(status="cancelled", project_id=input_data.project_id)
            if self._approval_decision != "approved":
                return {WorkflowName}Result(status="rejected", project_id=input_data.project_id)

        # Phase 3: Parallel processing with semaphore
        results = await self._process_items_parallel(
            prepared.items,
            max_concurrent=input_data.parallelism or 5,
        )

        # Phase 4: Verify + notify
        verified = await workflow.execute_activity(
            verify_results_activity,
            results,
            schedule_to_close_timeout=timedelta(minutes=30),
            retry_policy=STANDARD_RETRY_POLICY,
        )
        await workflow.execute_activity(
            notify_completion_activity,
            verified,
            schedule_to_close_timeout=timedelta(minutes=5),
            retry_policy=STANDARD_RETRY_POLICY,
        )

        return {WorkflowName}Result(
            status="completed",
            project_id=input_data.project_id,
            items_processed=len(results),
            success_count=verified.success_count,
            failure_count=verified.failure_count,
        )

    async def _wait_for_approval(self, timeout_hours: int) -> None:
        """Block until approval signal received or timeout."""
        try:
            await workflow.wait_condition(
                lambda: self._approval_received or self._cancelled,
                timeout=timedelta(hours=timeout_hours),
            )
        except asyncio.TimeoutError:
            workflow.logger.warning("Approval timeout after %dh", timeout_hours)
            self._approval_received = True
            self._approval_decision = "timeout_approved"  # Auto-approve on timeout (configurable)

    async def _process_items_parallel(self, items: list, max_concurrent: int) -> list:
        """Process items in parallel with semaphore-based concurrency limit."""
        semaphore = asyncio.Semaphore(max_concurrent)

        async def process_one(item):
            async with semaphore:
                return await workflow.execute_activity(
                    process_item_activity,
                    item,
                    schedule_to_close_timeout=timedelta(hours=1),
                    retry_policy=STANDARD_RETRY_POLICY,
                )

        return await asyncio.gather(*[process_one(item) for item in items])


# ─── Retry Policy ──────────────────────────────────────────────────────────────

STANDARD_RETRY_POLICY = RetryPolicy(
    initial_interval=timedelta(seconds=5),
    backoff_coefficient=2.0,
    maximum_interval=timedelta(minutes=5),
    maximum_attempts=3,
    non_retryable_error_types=[
        "ValidationError",         # Don't retry invalid inputs
        "ForbiddenOperationError", # Don't retry policy violations
        "ApprovalDeniedError",     # Don't retry explicit denials
    ],
)
```

---

## Activity Implementation Pattern

```python
# agents/temporal/activities/{workflow_name}_activities.py
from temporalio import activity
from pydantic import BaseModel
from agents.shared.ledger_client import LedgerClient


class {WorkflowName}Input(BaseModel):
    project_id:        str
    require_approval:  bool = True
    approval_timeout_hours: int = 24
    parallelism:       int = 5


class {WorkflowName}Result(BaseModel):
    status:            str          # "completed"|"cancelled"|"rejected"
    project_id:        str
    items_processed:   int = 0
    success_count:     int = 0
    failure_count:     int = 0


@activity.defn(name="prepare_{workflow_name}")
async def prepare_activity(input_data: {WorkflowName}Input) -> dict:
    """
    Preparation activity — fetch and validate all inputs.
    Idempotent: safe to retry.
    """
    activity.logger.info("Preparing %s for %s", "{workflow_name}", input_data.project_id)
    # Fetch items to process
    items = await fetch_items_for_project(input_data.project_id)
    await LedgerClient.record_stage(
        project_id=input_data.project_id,
        stage="{workflow_name}.prepare",
        output_summary=f"Prepared {len(items)} items",
    )
    return {"items": items}


@activity.defn(name="process_item_{workflow_name}")
async def process_item_activity(item: dict) -> dict:
    """Process a single item. Idempotent via item.id check."""
    # Heartbeat for long-running activities (prevents timeout)
    activity.heartbeat(f"Processing {item['id']}")
    # ... implementation
    return {"item_id": item["id"], "status": "success"}
```

---

## Worker Process

```python
# agents/temporal/worker.py
import asyncio
from temporalio.client import Client
from temporalio.worker import Worker

from .workflows.{workflow_name} import {WorkflowName}Workflow
from .activities.{workflow_name}_activities import (
    prepare_activity,
    process_item_activity,
    verify_results_activity,
    notify_completion_activity,
)

TEMPORAL_HOST = "temporal-frontend.temporal:7233"  # In-cluster Temporal service
TASK_QUEUE    = "{task_queue_name}"


async def main() -> None:
    client = await Client.connect(TEMPORAL_HOST)
    worker = Worker(
        client,
        task_queue=TASK_QUEUE,
        workflows=[{WorkflowName}Workflow],
        activities=[
            prepare_activity,
            process_item_activity,
            verify_results_activity,
            notify_completion_activity,
        ],
    )
    print(f"Worker running on task queue: {TASK_QUEUE}")
    await worker.run()


if __name__ == "__main__":
    asyncio.run(main())
```

---

## Acceptance Criteria

| # | Criterion |
|---|-----------|
| AC1 | Workflow resumes correctly after worker pod restart (durability test) |
| AC2 | Human approval signal unblocks workflow within 5 seconds of signal send |
| AC3 | `cancel` signal stops workflow gracefully — no partial state |
| AC4 | Parallel semaphore limits concurrency to `max_concurrent` value |
| AC5 | All activities are idempotent (safe to retry on failure) |
| AC6 | Activities call `activity.heartbeat()` for operations > 10 seconds |
| AC7 | Non-retryable error types configured to prevent infinite retry loops |
| AC8 | All workflow state changes recorded to Pipeline Ledger |
| AC9 | Workflow status queryable from Portal UI in real time |
| AC10 | Temporal UI (http://temporal-ui.temporal) shows workflow execution history |

---

*Temporal.io Workflow Scaffold Skill — AD Ports AI Portal — v1.0.0 — Owner: Orchestrator Squad*
