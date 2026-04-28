# Phase 24 — Fleet Upgrade & Framework Migration Agent (Gate 3 Checkpoint)

## Summary

Implement the **Fleet Upgrade Agent** — autonomously upgrades Angular, .NET, and Node.js frameworks across all registered services. Given a target version (e.g., Angular 21, .NET 10), the agent analyses breaking changes, generates migration patches, runs tests, and opens PRs for each affected service. Also handles the `framework-lifecycle-policy` — no framework more than 2 major versions behind the current release.

---

## Objectives

1. Implement Framework Lifecycle Policy enforcer (alerts when services fall behind).
2. Implement Angular upgrade generator (ng update + breaking change patching).
3. Implement .NET upgrade generator (TargetFramework bump + breaking API patches).
4. Implement Node.js/npm dependency upgrade generator.
5. Implement breaking change analyser (LLM-assisted change log analysis).
6. Implement parallel PR generator (one PR per service).
7. Implement test-driven validation (all tests must pass before PR is opened).
8. Implement rollback plan (generated alongside every upgrade PR).
9. Implement fleet campaign dashboard (progress across all services).
10. Conduct Gate 3 validation.

---

## Prerequisites

- Phase 19 (Project Registry — knows all services + framework versions).
- Phase 21 (PR Review Agent — auto-reviews upgrade PRs).
- Phase 07 (Capability Fabric — `framework-lifecycle-policy` skill + upgrade specs).
- Phase 12–13 (Backend + Frontend Agents — can apply targeted patches).

---

## Duration

**4 weeks** (last week = Gate 3 validation)

**Squad:** Platform Squad + Intelligence Squad (1 SRE + 1 Python/AI + 1 senior Angular + 1 senior .NET)

---

## Deliverables

| # | Deliverable | Acceptance Criterion |
|---|------------|---------------------|
| D1 | Framework Lifecycle Policy | Services falling > 1 major behind auto-alerted |
| D2 | Angular upgrade generator | `ng update @angular/core @angular/cli` + breaking change patches |
| D3 | .NET upgrade generator | `TargetFramework` bump + NuGet dependency updates |
| D4 | Node.js upgrade generator | `package.json` + lockfile updated; `npm audit` passes |
| D5 | Breaking change analyser | LLM reads Angular/dotnet migration guides → patch list |
| D6 | Parallel PR generator | 10 services upgraded in parallel; 10 separate PRs opened |
| D7 | Test-driven validation | All tests pass locally before PR opened |
| D8 | Rollback plan | Per-service rollback steps generated alongside upgrade PR |
| D9 | Fleet campaign dashboard | Progress bar + per-service status for active upgrade campaign |
| D10 | Gate 3 validation | Full Gate 3 checklist passes |

---

## Framework Lifecycle Policy

From `shared/instructions/framework-lifecycle-policy.md`:

```
Allowed lag: 1 major version behind the current stable release.
Alert threshold: 2 major versions behind.
Block threshold: 3 major versions behind (new features blocked until upgraded).
Schedule: Upgrades must complete within 90 days of new major release.
```

The Registry AKS sync job tracks current versions. The Lifecycle Policy enforcer runs weekly:

```python
async def enforce_framework_lifecycle_policy():
    latest = await fetch_latest_framework_versions()
    # e.g. { "angular": "21.0", "dotnet": "10.0", "nodejs": "22.0" }

    outdated_services = await registry_db.find_outdated_frameworks_all()
    for service in outdated_services:
        lag = calculate_major_version_lag(service.framework_version, latest[service.framework])
        if lag >= 2:
            await create_upgrade_work_package(service, latest[service.framework], urgency="ALERT")
        elif lag >= 3:
            await block_new_features(service)
            await create_upgrade_work_package(service, latest[service.framework], urgency="BLOCK")
```

---

## Angular Upgrade Generator

```python
# fleet_upgrade/angular_upgrader.py
async def upgrade_angular(service: Service, target_version: str) -> UpgradePatch:
    """
    Generates upgrade patch for an Angular MFE.
    1. Run ng update (deterministic)
    2. Analyse breaking changes from CHANGELOG.md
    3. Apply targeted fixes via LLM
    4. Run nx test + nx build
    5. Confirm all pass before opening PR
    """
    # Step 1: Determine exact breaking changes needed
    changes = await breaking_change_analyser.analyse(
        framework="angular",
        from_version=service.framework_version,
        to_version=target_version
    )
    # e.g. [BreakingChange("APP_INITIALIZER injection token deprecated", "use inject() instead")]

    # Step 2: Generate patches for each breaking change
    patches = []
    for change in changes:
        affected_files = await git.find_affected_files(service.repo, change.pattern)
        for file in affected_files:
            content = await git.read_file(service.repo, file)
            patched = await llm_gateway.apply_migration(content, change, tier="premium")
            patches.append(FilePatch(file=file, original=content, patched=patched))

    # Step 3: Update package.json versions
    patches.append(update_package_json(service, target_version))

    return UpgradePatch(
        service_id=service.id,
        from_version=service.framework_version,
        to_version=target_version,
        patches=patches,
        rollback_steps=generate_rollback_steps(patches)
    )
```

### Angular Breaking Change Analyser

```python
async def analyse_angular_breaking_changes(from_ver: str, to_ver: str) -> list[BreakingChange]:
    """
    Reads Angular CHANGELOG.md and migration guide via HTTP.
    Extracts breaking changes as structured patterns.
    """
    migration_guide = await http.get(
        f"https://angular.io/guide/update-to-version-{to_ver.split('.')[0]}"
    )

    prompt = f"""
You are analysing Angular {from_ver} → {to_ver} breaking changes.

Migration guide:
{migration_guide.text[:4000]}

Output a JSON array of breaking changes. Each item:
{{
  "description": "...",
  "pattern": "code pattern to search for",
  "fix": "how to fix it",
  "files_affected": ["*.ts", "*.html"]
}}
"""
    return await llm_gateway.complete_json(prompt, tier="standard")
```

---

## Parallel Upgrade Campaign

```python
# fleet_upgrade/campaign_runner.py
async def run_upgrade_campaign(framework: str, target_version: str) -> CampaignResult:
    """
    Upgrades all services using the specified framework to the target version.
    Services are upgraded in parallel (max 10 at a time).
    """
    services = await registry_db.find_services_by_framework(framework)
    services_to_upgrade = [s for s in services if needs_upgrade(s, target_version)]

    async with asyncio.TaskGroup() as tg:
        tasks = {}
        semaphore = asyncio.Semaphore(10)  # Max 10 concurrent upgrades

        for service in services_to_upgrade:
            async def upgrade_with_semaphore(svc):
                async with semaphore:
                    return await upgrade_service(svc, target_version)

            tasks[service.id] = tg.create_task(upgrade_with_semaphore(service))

    results = {sid: task.result() for sid, task in tasks.items()}
    return CampaignResult(
        total=len(services_to_upgrade),
        successful=sum(1 for r in results.values() if r.success),
        failed=sum(1 for r in results.values() if not r.success),
        prs_opened=[r.pr_url for r in results.values() if r.pr_url]
    )
```

---

## Fleet Campaign Dashboard

```html
<!-- fleet-upgrade/campaign-dashboard.component.ts -->
<div class="campaign-layout">
  <div class="campaign-header">
    <h2>Angular 21 Upgrade Campaign</h2>
    <p-progressBar [value]="campaign.progressPercent" />
    <span>{{ campaign.completed }}/{{ campaign.total }} services upgraded</span>
  </div>

  <p-table [value]="campaign.services" sortField="status" dataKey="id">
    <ng-template pTemplate="body" let-service>
      <tr>
        <td>{{ service.name }}</td>
        <td>{{ service.fromVersion }} → {{ service.toVersion }}</td>
        <td>
          <p-tag [value]="service.status"
                 [severity]="statusSeverity(service.status)" />
        </td>
        <td>
          <a [href]="service.prUrl" target="_blank" *ngIf="service.prUrl">
            View PR
          </a>
        </td>
        <td>{{ service.testResult }}</td>
      </tr>
    </ng-template>
  </p-table>
</div>
```

---

## Gate 3 Criteria

| # | Criterion | Measurement |
|---|-----------|------------|
| G3.1 | All registered services on framework versions within lifecycle policy | Registry version report |
| G3.2 | Angular upgrade campaign completed for all 5 test MFEs | Campaign dashboard 5/5 |
| G3.3 | .NET upgrade from 8 → 9 completed for all backend services | Registry version report |
| G3.4 | PR Review Agent scores all upgrade PRs 85+ | PR score distribution |
| G3.5 | Zero regressions after upgrade (all tests pass) | CI pipeline results |
| G3.6 | Fleet campaign completed in < 8 hours for 20 services | Campaign duration log |
| G3.7 | Rollback plan generated for every upgraded service | Rollback doc count |
| G3.8 | Vulnerability Radar shows 0 CRITICAL findings post-upgrade | Radar dashboard |
| G3.9 | Gate 2 criteria still passing | Automated regression run |
| G3.10 | PR Review Agent active on all registered repos (not just DGD) | GitLab webhook config |

---

## Step-by-Step Execution Plan

### Week 1: Framework Lifecycle Policy + Breaking Change Analyser

- [ ] Implement Framework Lifecycle Policy enforcer (weekly cron).
- [ ] Implement breaking change analyser for Angular.
- [ ] Implement breaking change analyser for .NET.
- [ ] Test: correctly identifies breaking changes between Angular 19 → 21.

### Week 2: Upgrade Generators

- [ ] Implement Angular upgrade generator (ng update + patch application).
- [ ] Implement .NET upgrade generator (TargetFramework + NuGet bumps).
- [ ] Implement Node.js upgrade generator.
- [ ] Test: Angular 19 MFE upgraded to 21; `nx build` passes.

### Week 3: Campaign Runner + PR Generation

- [ ] Implement parallel upgrade campaign runner (Semaphore, max 10).
- [ ] Implement rollback plan generator.
- [ ] Implement fleet campaign dashboard UI.
- [ ] Test: 5-service campaign completes; 5 PRs opened; all pass tests.

### Week 4: Gate 3 Validation

- [ ] Run full Gate 3 validation checklist.
- [ ] Fix any issues found.
- [ ] Record Gate 3 pass/fail in Pipeline Ledger with signed approvals.

---

*Phase 24 — Fleet Upgrade & Framework Migration Agent (Gate 3 Checkpoint) — AI Portal — v1.0*
