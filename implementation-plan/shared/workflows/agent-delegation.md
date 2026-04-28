# Workflow: Agent Delegation

## Workflow ID
`agent-delegation`

## Used By
Phase 10 Orchestrator (Stage 8) — dispatches specialist agents for code generation

## Description
Defines the contract between the Orchestration Agent and each specialist agent. Every specialist agent receives a typed WorkPackage, produces a typed AgentResult, and records events in the Pipeline Ledger. This document defines the common interface and per-agent specializations.

---

## Work Package Schema

```python
@dataclass
class WorkPackage:
    id:             str                 # UUID
    project_id:     str
    agent_type:     AgentType           # backend | frontend | database | integration | devops | qa
    input:          dict                # Agent-specific inputs
    dependencies:   list[str]           # IDs of WorkPackages that must complete first
    priority:       int                 # 1 (highest) – 5 (lowest)
    estimated_cost: float               # USD — used by budget policy
    timeout:        timedelta           # Max execution time
    retry_policy:   RetryPolicy
```

## Agent Result Schema

```python
@dataclass
class AgentResult:
    work_package_id: str
    agent_type:      AgentType
    status:          str                # completed | failed | partial
    artifacts:       list[Artifact]     # Generated files, repos, configs
    ledger_event_id: str               # Reference to Pipeline Ledger entry
    error:           str | None
    cost_usd:        float             # Actual LLM cost for this invocation
    duration_seconds: int
```

---

## Delegation Order (Standard Project)

```
Phase 1 (parallel):
  ├── BackendAgent    — generates all .NET services
  ├── DatabaseAgent   — generates DB migrations
  └── IntegrationAgent — wires RabbitMQ consumers

Phase 2 (after Phase 1):
  └── FrontendAgent   — generates Angular MFEs (needs API specs from Backend)

Phase 3 (parallel, after Phase 2):
  ├── QAAgent         — generates Playwright + Pact tests
  └── IntegrationTestAgent — generates Newman collection

Phase 4 (after all code generators):
  └── DevOpsAgent     — generates CI/CD pipeline + Helm + ArgoCD manifest
```

---

## Delegation Dispatcher

```python
async def execute_agents(state: OrchestrationState) -> OrchestrationState:
    """Execute all work packages in dependency order."""
    packages = state.approved_proposal.work_packages

    # Topological sort
    execution_order = topological_sort(packages)

    results = []
    for batch in execution_order:
        # Execute independent packages in parallel
        batch_results = await asyncio.gather(*[
            dispatch_to_agent(pkg) for pkg in batch
        ])
        results.extend(batch_results)

        # Check for failures
        failed = [r for r in batch_results if r.status == "failed"]
        if failed:
            await handle_agent_failures(failed, state)

    return {**state, "execution_results": results}
```

---

## Hook Engine Integration

Every agent call goes through the Hook Engine before execution:

```python
async def dispatch_to_agent(pkg: WorkPackage) -> AgentResult:
    # 1. Check Hook Engine
    decision = await hook_engine.evaluate(HookEvaluationRequest(
        action=AgentAction(
            agent_type=pkg.agent_type,
            operation="generate_code",
            project_id=pkg.project_id,
            estimated_cost_usd=pkg.estimated_cost
        ),
        caller=current_caller,
        project=current_project
    ))

    if not decision.allowed:
        return AgentResult(
            work_package_id=pkg.id,
            status="blocked",
            error=f"Hook Engine denied: {'; '.join(decision.deny_reasons)}"
        )

    # 2. Record start in Ledger
    await ledger.record(AgentStartedEvent(pkg.id, pkg.agent_type))

    # 3. Execute agent
    try:
        result = await AGENT_REGISTRY[pkg.agent_type].execute(pkg)
        await ledger.record(AgentCompletedEvent(pkg.id, result.artifacts))
        return result
    except Exception as e:
        await ledger.record(AgentFailedEvent(pkg.id, str(e)))
        raise
```

---

## Agent Registry

```python
AGENT_REGISTRY: dict[AgentType, BaseAgent] = {
    AgentType.BACKEND:            BackendSpecialistAgent(),
    AgentType.FRONTEND:           FrontendSpecialistAgent(),
    AgentType.DATABASE:           DatabaseAgent(),
    AgentType.INTEGRATION:        IntegrationAgent(),
    AgentType.DEVOPS:             DevOpsAgent(),
    AgentType.QA:                 QAAutomationAgent(),
    AgentType.INTEGRATION_TEST:   IntegrationTestAgent(),
    AgentType.FLEET_UPGRADE:      FleetUpgradeAgent(),
    AgentType.PR_REVIEW:          PRReviewAgent(),
    AgentType.BA:                 BAStoryAgent(),
}
```

---

## Retry Policy

```python
DEFAULT_RETRY_POLICY = RetryPolicy(
    max_attempts=3,
    backoff_strategy="exponential",
    initial_delay=timedelta(seconds=5),
    max_delay=timedelta(minutes=5),
    retryable_errors=[TimeoutError, LLMRateLimitError, TemporaryNetworkError],
    non_retryable_errors=[ValidationError, AuthorizationError, BudgetExceededError]
)
```

---

*shared/workflows/agent-delegation.md — AI Portal — v1.0*
