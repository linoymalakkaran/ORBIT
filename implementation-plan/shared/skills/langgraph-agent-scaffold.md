# Skill: LangGraph Agent Scaffold

## Skill ID
`langgraph-agent-scaffold`

## Version
`1.0.0`

## Used By
- Phase 10 (Orchestration Agent Core)
- Phase 11 (Architecture Proposal node)
- Phase 20 (Health Monitor anomaly detection graph)
- Any new AI agent added to the platform

## Description
Standard pattern for creating a LangGraph-based agent for the AD Ports AI Portal. Covers state definition, node implementation, graph wiring, Temporal.io durability wrapper, error recovery, cost tracking, and integration with the Orchestration platform.

---

## Skill Inputs

```json
{
  "agentName": "string",           // e.g. "vulnerability_radar_agent"
  "agentDisplayName": "string",    // e.g. "Vulnerability Radar Agent"
  "stateFields": [                 // Fields in the agent's state TypedDict
    { "name": "string", "type": "string", "description": "string" }
  ],
  "nodes": [                       // Graph nodes
    {
      "name": "string",
      "type": "llm|deterministic|tool_call|human_review",
      "llmTier": "premium|standard|economy|sovereign",
      "description": "string"
    }
  ],
  "edges": [                       // Graph edges including conditional
    { "from": "string", "to": "string|list", "condition": "string|null" }
  ],
  "temporalEnabled": true,
  "ledgerEnabled": true
}
```

---

## Output Artefacts

```
agents/{agent_name}/
├── __init__.py
├── state.py          ← State TypedDict definition
├── graph.py          ← LangGraph StateGraph wiring
├── nodes/
│   ├── __init__.py
│   └── {node_name}.py  ← One file per node
├── temporal/
│   ├── workflow.py   ← Temporal workflow wrapping the LangGraph
│   └── activities.py ← Long-running activities
├── evaluation/
│   ├── harness.py    ← Evaluation harness
│   └── golden_cases/ ← Golden test inputs
└── tests/
    ├── unit/
    └── integration/
```

---

## State Pattern

```python
# agents/{agent_name}/state.py
from typing import TypedDict, Annotated
from langgraph.graph.message import add_messages


class {AgentName}State(TypedDict):
    """State for the {AgentDisplayName}.
    
    All fields are optional except project_id and run_id.
    """
    # --- Identity ---
    project_id:    str
    run_id:        str

    # --- Inputs (populated at graph entry) ---
    raw_input:     str | None
    document_uris: list[str]

    # --- Stage outputs (None until each stage completes) ---
    parsed_input:  dict | None
    analysis:      dict | None
    result:        dict | None

    # --- Control ---
    current_node:  str
    retry_count:   int
    max_retries:   int          # default 3
    error:         str | None
    cancelled:     bool

    # --- Accumulate LLM cost (cents) ---
    total_cost_cents: float
```

---

## Node Pattern

```python
# agents/{agent_name}/nodes/analysis_node.py
import logging
from typing import Any

from agents.shared.litellm_client import litellm_client, LLMTier
from agents.shared.cost_tracker import CostTracker
from agents.shared.ledger_client import LedgerClient
from ..state import {AgentName}State

logger = logging.getLogger(__name__)

ANALYSIS_SYSTEM_PROMPT = """
You are the AD Ports {agent_display_name}.
<Detailed instructions here>
Output ONLY valid JSON matching the schema provided.
""".strip()


async def analysis_node(state: {AgentName}State) -> dict[str, Any]:
    """
    Analyse the parsed input and produce a structured result.
    
    LLM Tier: {tier} — {rationale}
    """
    logger.info("analysis_node: project=%s run=%s", state["project_id"], state["run_id"])

    # 1. Build prompt
    user_message = f"""
Input:
{state['parsed_input']}

Produce analysis JSON:
{ANALYSIS_OUTPUT_SCHEMA}
""".strip()

    # 2. Call LLM via LiteLLM gateway (with cost tracking)
    async with CostTracker(state["project_id"], "analysis_node") as tracker:
        response = await litellm_client.structured_completion(
            tier=LLMTier.STANDARD,
            system_prompt=ANALYSIS_SYSTEM_PROMPT,
            user_message=user_message,
            output_schema=AnalysisResult,
        )
        tracker.record(response.usage)

    # 3. Record to Pipeline Ledger
    await LedgerClient.record_stage(
        project_id=state["project_id"],
        stage="analysis_node",
        input_summary=str(state["parsed_input"])[:500],
        output_summary=str(response.data)[:500],
    )

    return {
        "analysis": response.data.model_dump(),
        "total_cost_cents": state["total_cost_cents"] + response.cost_cents,
        "current_node": "analysis_node",
    }


async def analysis_node_error_handler(state: {AgentName}State, error: Exception) -> dict:
    """Return error state update — do NOT raise."""
    logger.error("analysis_node failed: %s", error, exc_info=True)
    return {
        "error": str(error),
        "retry_count": state["retry_count"] + 1,
    }
```

---

## Graph Wiring Pattern

```python
# agents/{agent_name}/graph.py
from langgraph.graph import StateGraph, END
from .state import {AgentName}State
from .nodes.parse_node import parse_input_node
from .nodes.analysis_node import analysis_node
from .nodes.result_node import produce_result_node


def should_retry(state: {AgentName}State) -> str:
    """Conditional edge — retry on transient error, fail on max retries."""
    if state.get("error") and state["retry_count"] < state["max_retries"]:
        return "parse_input"     # Retry from start
    if state.get("error"):
        return END               # Max retries exhausted
    return "analysis"            # Happy path


def build_graph() -> StateGraph:
    graph = StateGraph({AgentName}State)

    # Add nodes
    graph.add_node("parse_input", parse_input_node)
    graph.add_node("analysis", analysis_node)
    graph.add_node("produce_result", produce_result_node)

    # Entry point
    graph.set_entry_point("parse_input")

    # Edges
    graph.add_conditional_edges("parse_input", should_retry)
    graph.add_edge("analysis", "produce_result")
    graph.add_edge("produce_result", END)

    return graph.compile()


# Singleton compiled graph
AGENT_GRAPH = build_graph()
```

---

## Temporal.io Durability Wrapper

```python
# agents/{agent_name}/temporal/workflow.py
from datetime import timedelta
from temporalio import workflow
from temporalio.common import RetryPolicy

from ..state import {AgentName}State


@workflow.defn(name="{agent_name}_workflow")
class {AgentName}Workflow:
    """Temporal workflow wrapping the LangGraph for durable execution."""

    @workflow.run
    async def run(self, input_state: dict) -> dict:
        # Execute LangGraph via Temporal activity (survives worker restarts)
        result = await workflow.execute_activity(
            "run_{agent_name}_graph",
            input_state,
            schedule_to_close_timeout=timedelta(hours=2),
            retry_policy=RetryPolicy(
                initial_interval=timedelta(seconds=5),
                backoff_coefficient=2.0,
                maximum_interval=timedelta(minutes=5),
                maximum_attempts=3,
            ),
        )
        return result
```

---

## LiteLLM Gateway Client

```python
# agents/shared/litellm_client.py
from enum import StrEnum
import litellm
from pydantic import BaseModel


class LLMTier(StrEnum):
    PREMIUM   = "premium"     # Claude Sonnet 4.x — judgment/review
    STANDARD  = "standard"    # GPT-4o — general generation
    ECONOMY   = "economy"     # DeepSeek-V3 — bulk/cheap tasks
    SOVEREIGN = "sovereign"   # Llama 3.3 self-hosted — classified data


TIER_MODEL_MAP: dict[LLMTier, str] = {
    LLMTier.PREMIUM:   "claude-sonnet-4",
    LLMTier.STANDARD:  "azure/gpt-4o",
    LLMTier.ECONOMY:   "deepseek/deepseek-chat",
    LLMTier.SOVEREIGN: "openai/llama-3.3-70b",   # Points to vLLM on AKS
}


async def structured_completion[T: BaseModel](
    tier: LLMTier,
    system_prompt: str,
    user_message: str,
    output_schema: type[T],
    temperature: float = 0.1,
) -> T:
    """Call LLM and parse response into Pydantic model."""
    response = await litellm.acompletion(
        model=TIER_MODEL_MAP[tier],
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user",   "content": user_message},
        ],
        temperature=temperature,
        response_format=output_schema,
    )
    content = response.choices[0].message.content
    return output_schema.model_validate_json(content)
```

---

## Evaluation Harness Pattern

```python
# agents/{agent_name}/evaluation/harness.py
import json
import asyncio
from pathlib import Path
from ..graph import AGENT_GRAPH


async def run_golden_cases(golden_dir: str = "golden_cases") -> dict:
    results = {"passed": 0, "failed": 0, "cases": []}
    
    for case_file in Path(golden_dir).glob("*.json"):
        case = json.loads(case_file.read_text())
        try:
            output = await AGENT_GRAPH.ainvoke(case["input"])
            passed = validate_output(output, case["expected"])
            results["cases"].append({
                "name": case_file.stem,
                "passed": passed,
                "output": output,
            })
            if passed:
                results["passed"] += 1
            else:
                results["failed"] += 1
        except Exception as e:
            results["failed"] += 1
            results["cases"].append({"name": case_file.stem, "error": str(e)})

    pass_rate = results["passed"] / len(results["cases"]) if results["cases"] else 0
    results["pass_rate"] = pass_rate
    results["gate_passed"] = pass_rate >= 0.75  # 75% minimum
    return results
```

---

## Acceptance Criteria

| # | Criterion |
|---|-----------|
| AC1 | State TypedDict defines all fields; no untyped `dict` used |
| AC2 | Every node returns a partial state dict (not full state) |
| AC3 | Every LLM call goes through `litellm_client.structured_completion` — no direct OpenAI/Anthropic SDK |
| AC4 | Cost tracked and accumulated in `total_cost_cents` state field |
| AC5 | Every state-changing node records a Pipeline Ledger event |
| AC6 | Graph handles error state — never raises unhandled exception to caller |
| AC7 | Temporal workflow wraps the entire graph for durability |
| AC8 | Evaluation harness exists with ≥ 3 golden cases per agent |
| AC9 | Golden case pass rate ≥ 75% before agent is promoted to staging |
| AC10 | All LLM calls use `temperature ≤ 0.2` for deterministic outputs |

---

*LangGraph Agent Scaffold Skill — AD Ports AI Portal — v1.0.0 — Owner: Orchestrator Squad*
