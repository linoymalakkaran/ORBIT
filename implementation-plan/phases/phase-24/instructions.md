# Instructions — Phase 24: Fleet Upgrade Agent

> Add this file to your IDE's custom instructions when building or operating the Fleet Upgrade Agent.

---

## Context

You are building the **AD Ports Fleet Upgrade Agent** — a Temporal-backed autonomous agent that manages coordinated framework upgrades across the entire AD Ports service fleet. The agent discovers all services using a given framework version, analyzes breaking changes, generates upgrade patches, and orchestrates a safe wave-based rollout with automatic pause on failures.

---

## Fleet Discovery

```python
# Fleet is discovered from the Portal's service registry
async def discover_fleet_services(
    framework: str,
    current_version: str,
) -> list[FleetService]:
    """
    Returns all services using framework@current_version.
    Data sourced from: Capability Fabric + GitLab API + Helm release annotations.
    """
    services = await service_registry.query(
        labels={"framework": framework, "framework_version": current_version}
    )
    return [
        FleetService(
            service_id=s.id,
            name=s.name,
            repo_url=s.git_repo,
            risk_level=classify_risk(s),   # low | medium | high
            current_version=current_version,
        )
        for s in services
    ]

def classify_risk(service: Service) -> str:
    """Risk based on: prod traffic, has-live-users, framework dependencies."""
    if service.environment == "prod" and service.active_user_count > 100:
        return "high"
    if service.environment == "prod":
        return "medium"
    return "low"
```

## Wave Planning Strategy

```python
def plan_upgrade_waves(services: list[FleetService]) -> list[UpgradeWave]:
    """
    Wave order: low risk → medium risk → high risk
    Max 5 concurrent services per wave.
    """
    low    = [s for s in services if s.risk_level == "low"]
    medium = [s for s in services if s.risk_level == "medium"]
    high   = [s for s in services if s.risk_level == "high"]

    waves = []
    for group in [low, medium, high]:
        for i in range(0, len(group), 5):
            waves.append(UpgradeWave(
                services=group[i:i+5],
                risk_level=group[0].risk_level if group else "low",
            ))
    return waves
```

## Breaking Change Analyser

```python
BREAKING_CHANGE_ANALYSERS = {
    "dotnet":  DotNetBreakingChangeAnalyser,   # Parses .NET migration docs
    "angular": AngularBreakingChangeAnalyser,  # Parses Angular update.angular.io
    "litellm": LiteLLMBreakingChangeAnalyser,  # Parses LiteLLM changelog
}

class DotNetBreakingChangeAnalyser:
    async def analyse(self, from_version: str, to_version: str) -> list[BreakingChange]:
        """
        Uses the LLM (standard tier) to parse .NET migration guides and identify
        changes affecting the codebase. Returns structured list of:
        - API renames
        - Removed APIs
        - Behavioural changes
        - Required package updates
        """
        ...
```

## Upgrade Patch Generation

The agent generates a git patch for each breaking change:

```python
UPGRADE_PATCH_GENERATORS = {
    "api_rename":      generate_rename_patch,       # Uses Roslyn for C#, TS compiler for Angular
    "package_update":  generate_package_update,     # Updates .csproj or package.json
    "config_change":   generate_config_patch,       # Updates appsettings.json / environment files
    "migration":       generate_ef_migration,       # Runs `dotnet ef migrations add`
}
```

## Approval Gate (Two-Person Rule)

Fleet upgrades to production require TWO approvals:
1. **Architect** — reviews the breaking change analysis and patch strategy
2. **Delivery Lead** — authorises the production wave rollout

```python
# Signals the Temporal workflow waits for
@workflow.signal
async def approve_campaign(self, approver: ApprovalSignal) -> None:
    if approver.role == "architect" and not self._state.architect_approved:
        self._state.architect_approved = True
        self._state.approvals.append(approver)
    elif approver.role == "delivery_lead" and not self._state.lead_approved:
        self._state.lead_approved = True
        self._state.approvals.append(approver)

# Campaign starts execution only when both approvals received
```

## Auto-Pause Threshold

```python
# After each wave, check failure rate
# If > 20% of services in a wave fail, PAUSE the campaign

FAILURE_RATE_THRESHOLD = 0.20

if failed_count / total_in_wave > FAILURE_RATE_THRESHOLD:
    logger.warning("Auto-pausing fleet upgrade — failure rate %.0f%%", 
                   failed_count / total_in_wave * 100)
    self._state.status = CampaignStatus.PAUSED
    await notify_delivery_lead("Fleet upgrade paused — human review required")
    # Wait for resume signal
    await workflow.wait_condition(lambda: self._state.status == CampaignStatus.ACTIVE)
```

## Forbidden Patterns

| Pattern | Reason |
|---------|--------|
| Upgrading all services in one wave | Wave approach exists to limit blast radius |
| Starting production wave without both approvals | Two-person rule — enforced by Hook Engine |
| Skipping `dotnet build` check after patch | Generated patches must compile before fleet run |
| Cancelling a campaign mid-wave | Must pause first, then cancel after wave completes |

---

*Instructions — Phase 24 — AD Ports AI Portal — Applies to: Platform Squad + Delivery Agents Squad*
