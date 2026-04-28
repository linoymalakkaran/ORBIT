# Workflow: Fleet Upgrade Campaign

## Workflow ID
`fleet-upgrade-campaign`

## Used By
Phase 24 — Fleet Upgrade & Framework Migration Agent

## Description
Defines the durable Temporal.io + LangGraph workflow for executing a portfolio-wide framework upgrade campaign. A campaign upgrades a specific framework (e.g., .NET 9 → .NET 10, Angular 19 → Angular 20) across all eligible projects in the fleet in controlled waves with automated verification between waves.

---

## Campaign State Definition

```python
# agents/fleet_upgrade/state.py
from typing import TypedDict, Literal


class ProjectUpgradeStatus(TypedDict):
    project_id:        str
    project_name:      str
    current_version:   str
    target_version:    str
    status:            Literal["pending", "in_progress", "success", "failed", "skipped"]
    branch_name:       str | None
    pr_url:            str | None
    pr_merged:         bool
    test_results:      dict | None
    error_message:     str | None
    started_at:        str | None
    completed_at:      str | None


class FleetUpgradeCampaignState(TypedDict):
    # Campaign identity
    campaign_id:       str
    framework:         str              # "dotnet", "angular", "nodejs", "postgresql"
    current_version:   str              # e.g. "9.0"
    target_version:    str              # e.g. "10.0"
    
    # Wave planning
    eligible_projects: list[str]        # Project IDs from Registry scan
    excluded_projects: list[str]        # Manually excluded or exception-approved
    wave_plan:         list[list[str]]  # [[wave_1_project_ids], [wave_2_ids], ...]
    current_wave:      int
    
    # Per-project status
    project_statuses:  list[ProjectUpgradeStatus]
    
    # Approval
    campaign_approved: bool
    approver_id:       str | None
    approval_time:     str | None
    
    # Results
    success_count:     int
    failed_count:      int
    skip_count:        int
    
    # Control
    paused:            bool             # Operator pause between waves
    cancelled:         bool
    error:             str | None
```

---

## Temporal Workflow Definition

```python
# agents/temporal/workflows/fleet_upgrade_campaign.py
from datetime import timedelta
from temporalio import workflow
from temporalio.common import RetryPolicy
import asyncio


@workflow.defn(name="fleet_upgrade_campaign")
class FleetUpgradeCampaignWorkflow:
    """
    Fleet Upgrade Campaign — upgrades a framework across the entire project portfolio.
    
    Campaign phases:
    1. Scan fleet to identify eligible projects
    2. Break-change analysis per project
    3. Human approval gate (architect + DevOps lead sign-off)
    4. Wave 1: Low-risk projects (non-production, pilot projects)
    5. Verify Wave 1 results → proceed or pause
    6. Wave 2: Medium-risk projects
    7. Wave 3+: High-risk / production-critical projects
    8. Campaign completion report
    
    Duration: Hours to days depending on fleet size.
    """

    def __init__(self) -> None:
        self._campaign_approved     = False
        self._wave_proceed_signal   = False
        self._pause_requested       = False
        self._cancelled             = False
        self._current_phase         = "initializing"

    # ── Signals ──────────────────────────────────────────────────────────────

    @workflow.signal
    async def approve_campaign(self, approver_id: str) -> None:
        """Sent by Portal UI after architect + DevOps lead review."""
        self._campaign_approved = True
        self._approver_id = approver_id
        workflow.logger.info("Campaign approved by %s", approver_id)

    @workflow.signal
    async def proceed_next_wave(self) -> None:
        """Sent by Portal UI to advance to the next wave after operator review."""
        self._wave_proceed_signal = True

    @workflow.signal
    async def pause_campaign(self) -> None:
        """Pause after current wave completes."""
        self._pause_requested = True

    @workflow.signal
    async def cancel_campaign(self) -> None:
        """Cancel campaign immediately."""
        self._cancelled = True

    # ── Queries ───────────────────────────────────────────────────────────────

    @workflow.query
    def get_status(self) -> dict:
        return {
            "phase":    self._current_phase,
            "approved": self._campaign_approved,
            "paused":   self._pause_requested,
            "cancelled": self._cancelled,
        }

    # ── Main execution ────────────────────────────────────────────────────────

    @workflow.run
    async def run(self, input_data: dict) -> dict:
        campaign_id  = input_data["campaign_id"]
        framework    = input_data["framework"]
        target_ver   = input_data["target_version"]

        workflow.logger.info("Fleet upgrade campaign started: %s → %s", framework, target_ver)

        # Phase 1: Fleet scan
        self._current_phase = "fleet_scan"
        eligible = await workflow.execute_activity(
            "scan_fleet_for_upgrades",
            { "framework": framework, "target_version": target_ver },
            schedule_to_close_timeout=timedelta(minutes=30),
            retry_policy=RETRY_POLICY,
        )

        # Phase 2: Breaking change analysis (parallel per project)
        self._current_phase = "breaking_change_analysis"
        analysis_results = await self._analyse_projects_parallel(
            eligible["project_ids"], framework, target_ver, max_concurrent=10
        )

        # Phase 3: Generate wave plan
        wave_plan = await workflow.execute_activity(
            "generate_wave_plan",
            { "analysis_results": analysis_results, "campaign_id": campaign_id },
            schedule_to_close_timeout=timedelta(minutes=10),
        )

        # Phase 4: Human approval gate (24-hour timeout)
        self._current_phase = "awaiting_approval"
        await workflow.wait_condition(
            lambda: self._campaign_approved or self._cancelled,
            timeout=timedelta(hours=24),
        )
        if self._cancelled:
            return {"status": "cancelled", "campaign_id": campaign_id}

        # Phase 5: Execute waves
        self._current_phase = "executing_waves"
        all_results = []
        for wave_index, wave_projects in enumerate(wave_plan["waves"]):
            wave_results = await self._execute_wave(
                wave_index, wave_projects, framework, target_ver, max_concurrent=5
            )
            all_results.extend(wave_results)

            # Pause if requested or if wave failure rate > 20%
            failure_rate = sum(1 for r in wave_results if r["status"] == "failed") / len(wave_results)
            if self._cancelled:
                break
            if self._pause_requested or failure_rate > 0.2:
                self._current_phase = f"paused_after_wave_{wave_index + 1}"
                self._pause_requested = False
                self._wave_proceed_signal = False
                await workflow.wait_condition(
                    lambda: self._wave_proceed_signal or self._cancelled,
                    timeout=timedelta(hours=72),
                )
                if self._cancelled:
                    break

        # Phase 6: Campaign completion report
        self._current_phase = "completed"
        await workflow.execute_activity(
            "generate_campaign_report",
            { "campaign_id": campaign_id, "results": all_results },
            schedule_to_close_timeout=timedelta(minutes=30),
        )

        success = sum(1 for r in all_results if r["status"] == "success")
        failed  = sum(1 for r in all_results if r["status"] == "failed")
        return {
            "status": "completed",
            "campaign_id": campaign_id,
            "total": len(all_results),
            "success": success,
            "failed": failed,
        }

    async def _analyse_projects_parallel(
        self, project_ids, framework, target_ver, max_concurrent
    ):
        semaphore = asyncio.Semaphore(max_concurrent)

        async def analyse_one(project_id):
            async with semaphore:
                return await workflow.execute_activity(
                    "analyse_breaking_changes",
                    { "project_id": project_id, "framework": framework, "target_version": target_ver },
                    schedule_to_close_timeout=timedelta(hours=1),
                    retry_policy=RETRY_POLICY,
                )

        return await asyncio.gather(*[analyse_one(pid) for pid in project_ids])

    async def _execute_wave(self, wave_index, project_ids, framework, target_ver, max_concurrent):
        semaphore = asyncio.Semaphore(max_concurrent)

        async def upgrade_one(project_id):
            async with semaphore:
                return await workflow.execute_activity(
                    "upgrade_single_project",
                    {
                        "project_id": project_id,
                        "framework": framework,
                        "target_version": target_ver,
                        "wave_index": wave_index,
                    },
                    schedule_to_close_timeout=timedelta(hours=4),
                    retry_policy=RETRY_POLICY,
                )

        return await asyncio.gather(*[upgrade_one(pid) for pid in project_ids])


RETRY_POLICY = RetryPolicy(
    initial_interval=timedelta(seconds=10),
    backoff_coefficient=2.0,
    maximum_interval=timedelta(minutes=10),
    maximum_attempts=3,
    non_retryable_error_types=["ValidationError", "ForbiddenOperationError"],
)
```

---

## Activity: `upgrade_single_project`

```python
from temporalio import activity


@activity.defn(name="upgrade_single_project")
async def upgrade_single_project_activity(input_data: dict) -> dict:
    """
    Execute framework upgrade for a single project.
    Idempotent: checks if upgrade branch already exists before creating.
    
    Steps:
    1. Clone project repository
    2. Create upgrade branch (upgrade/{framework}-{target_version})
    3. Run framework-specific upgrade generator (Backend/Frontend Agent in tool mode)
    4. Commit changes
    5. Push branch and open PR
    6. Run CI (wait up to 45 minutes)
    7. Record result in Pipeline Ledger
    """
    project_id   = input_data["project_id"]
    framework    = input_data["framework"]
    target_ver   = input_data["target_version"]

    activity.heartbeat(f"Starting upgrade for {project_id}")

    # Check if already done (idempotency)
    existing_pr = await check_existing_upgrade_pr(project_id, framework, target_ver)
    if existing_pr:
        return { "project_id": project_id, "status": "skipped", "pr_url": existing_pr["url"] }

    # Clone + upgrade
    activity.heartbeat(f"Cloning {project_id}")
    branch = f"upgrade/{framework}-{target_ver.replace('.', '-')}"
    await gitlab_mcp.create_branch(project_id, branch)

    activity.heartbeat(f"Running upgrade generator for {project_id}")
    changes = await run_upgrade_generator(project_id, framework, target_ver)
    
    activity.heartbeat(f"Committing changes for {project_id}")
    await gitlab_mcp.commit_changes(project_id, branch, changes,
        message=f"chore: upgrade {framework} to {target_ver} [fleet-campaign]")
    
    pr = await gitlab_mcp.create_pr(project_id, branch,
        title=f"[Fleet Upgrade] {framework} → {target_ver}",
        description=generate_pr_description(changes))

    activity.heartbeat(f"Waiting for CI on {project_id}")
    ci_result = await wait_for_ci(project_id, branch, timeout_minutes=45)

    await ledger_client.record_fleet_upgrade(project_id, framework, target_ver, ci_result)

    return {
        "project_id": project_id,
        "status": "success" if ci_result["passed"] else "failed",
        "pr_url": pr["url"],
        "ci_passed": ci_result["passed"],
    }
```

---

## Wave Planning Strategy

```
Wave 1 (low risk, max 20% of fleet):
  - Non-production environments only
  - Pilot projects volunteered for early upgrades
  - Projects with high test coverage (≥ 80%)
  
Wave 2 (medium risk, 30% of fleet):
  - Staging-validated projects
  - Non-customer-facing internal tools
  
Wave 3+ (high risk, remaining fleet):
  - Customer-facing production services
  - Payment/customs-critical services (CRITICAL tier)
  - Each wave pauses for human review before proceeding
```

---

## Failure Handling

| Scenario | Behaviour |
|---------|-----------|
| CI fails for a project | Marks project `failed`; continues other projects in wave |
| > 20% projects fail in a wave | Auto-pause campaign; require human review before next wave |
| Worker pod restarts mid-campaign | Temporal resumes from last completed activity |
| Human doesn't approve within 24h | Campaign auto-cancels (approval timeout) |
| Fleet-wide CI outage | Pause campaign; resume when CI is healthy |
| Breaking change found mid-wave | Skip project; flag for manual intervention |

---

## Fleet Upgrade Dashboard

The Portal exposes a real-time campaign dashboard (Angular component):

```
Campaign: .NET 9 → .NET 10  
Started: 2026-04-28  |  Status: Wave 2 of 3  |  Approved by: john.smith@adports.ae

┌─────────────────────────────────────────────────────────────┐
│  Wave 1 (Completed) ✅  10/10 success  0 failed             │
│  Wave 2 (In Progress) 🔄  3/8 success  1 failed  4 pending  │
│  Wave 3 (Pending) ⏳  12 projects                           │
└─────────────────────────────────────────────────────────────┘

[Pause Campaign]  [Proceed to Wave 3]  [Cancel Campaign]
```

---

*Fleet Upgrade Campaign Workflow — AD Ports AI Portal — v1.0.0 — Owner: Delivery Agents Squad*
