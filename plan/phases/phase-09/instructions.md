# Instructions — Phase 09: Orchestrator Core

> Add this file to your IDE's custom instructions when working on the Orchestrator service.

---

## Context

You are working on the **AD Ports Orchestrator** — the central coordination engine that manages the lifecycle of every AI task. The Orchestrator is a Python FastAPI service backed by LangGraph (for multi-step state machine logic) and Temporal.io (for durable long-running workflows). It is the single entry point from the Portal UI to all AI agents.

---

## Orchestrator Architecture

```
Portal UI / API Gateway (Kong)
    │
    ▼
Orchestrator FastAPI  ─── Hook Engine (OPA) — pre-action check
    │                 ─── LiteLLM Gateway — provider-agnostic LLM
    │                 ─── Capability Fabric API — skills/specs
    │                 ─── Pipeline Ledger — append event
    │
    ├─► LangGraph State Machine   ← For multi-step, branching AI reasoning
    └─► Temporal.io Workflow      ← For long-running, durable tasks (>5 min)
```

## Task Lifecycle States

```python
class TaskStatus(str, Enum):
    PENDING      = "pending"       # Queued, not started
    VALIDATING   = "validating"    # Pre-hook engine check
    PLANNING     = "planning"      # Intent extraction + work package decomposition
    EXECUTING    = "executing"     # Agent(s) running
    REVIEWING    = "reviewing"     # Awaiting human approval
    COMPLETED    = "completed"     # All artefacts delivered
    FAILED       = "failed"        # Terminal failure
    CANCELLED    = "cancelled"     # User or system cancelled
```

## LangGraph State Machine Pattern

```python
# Every orchestrated flow is a LangGraph StateGraph
class OrchestratorState(TypedDict):
    task_id:        str
    project_id:     str
    caller:         dict
    input:          dict
    work_packages:  list[dict]
    results:        list[dict]
    errors:         list[str]
    status:         str

def build_orchestrator_graph() -> StateGraph:
    graph = StateGraph(OrchestratorState)

    graph.add_node("intent_extraction",     intent_extraction_node)
    graph.add_node("work_package_decomp",   work_package_decomp_node)
    graph.add_node("agent_dispatch",        agent_dispatch_node)
    graph.add_node("result_assembly",       result_assembly_node)
    graph.add_node("ledger_record",         ledger_record_node)

    graph.add_edge(START, "intent_extraction")
    graph.add_edge("intent_extraction", "work_package_decomp")
    graph.add_edge("work_package_decomp", "agent_dispatch")
    graph.add_edge("agent_dispatch", "result_assembly")
    graph.add_edge("result_assembly", "ledger_record")
    graph.add_edge("ledger_record", END)

    return graph.compile(checkpointer=PostgresSaver(...))
```

## Agent Delegation Pattern

```python
# agent_dispatch_node: routes each WorkPackage to the correct specialist agent
AGENT_REGISTRY = {
    "backend":   BackendSpecialistAgent,
    "frontend":  FrontendSpecialistAgent,
    "devops":    DevOpsAgent,
    "qa":        QaAgent,
    "ba_pm":     BaPmAgent,
}

async def agent_dispatch_node(state: OrchestratorState) -> OrchestratorState:
    tasks = []
    for wp in state["work_packages"]:
        agent_class = AGENT_REGISTRY[wp["agent_type"]]
        tasks.append(agent_class(wp).run())

    # Parallel dispatch for independent work packages
    results = await asyncio.gather(*tasks, return_exceptions=True)
    ...
```

## Temporal vs LangGraph Decision Rule

| Use LangGraph when... | Use Temporal when... |
|----------------------|---------------------|
| Task completes in < 5 min | Task may take hours or days |
| No human-in-the-loop waits | Requires human approval signals |
| Single execution attempt | Must be durable across server restarts |
| Branching based on LLM output | Sequential, predictable steps |
| Examples: ticket implementation | Examples: fleet upgrade campaign |

## Forbidden Patterns

| Pattern | Reason |
|---------|--------|
| Calling an MCP tool directly without Hook Engine check | Policy bypass |
| Storing LLM responses in-memory only (no checkpointer) | State lost on restart |
| Dispatching all work packages sequentially | Parallel packages must run concurrently |
| Returning 200 OK before Hook Engine approves | Client sees success before policy check |

---

*Instructions — Phase 09 — AD Ports AI Portal — Applies to: Platform Squad*
