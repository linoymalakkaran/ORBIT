# Phase 10 — Orchestration Agent Core

## Summary

This is the **most critical phase** of the entire project. The Orchestration Agent is the heart of the AI Portal — the single entry point for all complex AI-driven work. It reads intent from BRD/HLD/ICD documents, consults the capability fabric, generates architecture proposals, manages the review cycle, and delegates to specialist agents. Built on LangGraph for deterministic state machine flow and Temporal.io for durable long-running orchestrations.

---

## Objectives

1. Implement the LangGraph state machine for the full 9-stage orchestration pipeline.
2. Implement intent extraction from BRD/HLD/ICD documents.
3. Implement standards consultation (queries Fabric API for relevant skills/specs/instructions).
4. Implement the LiteLLM gateway integration (provider-agnostic LLM routing).
5. Implement the architecture proposal generator (draw.io + OpenAPI drafts + component decomposition).
6. Implement the agent context assembler (feeds context into specialist agents).
7. Implement Temporal.io workflow for durable long-running orchestrations.
8. Implement the agent cost tracker (per-orchestration LLM token + cost accounting).
9. Wire the Orchestrator to the Pipeline Ledger (every state transition = Ledger event).
10. Implement the evaluation harness with golden AD Ports BRD projects.

---

## Prerequisites

- Phase 06 (Shared Project Context — Redis).
- Phase 07 (Capability Fabric — Skills/Specs/Instructions API).
- Phase 08 (Keycloak MCP + GitLab MCP).
- Phase 09 (All MCP servers deployed).
- Phase 05 (Pipeline Ledger operational).
- LiteLLM gateway configured with Claude Sonnet + Azure OpenAI.

---

## Duration

**4 weeks** — the longest phase. Requires daily stand-ups and mid-week architecture reviews.

**Squad:** Orchestrator Squad (2 ML/AI engineers + 1 senior .NET + 1 Python)

---

## Deliverables

| # | Deliverable | Acceptance Criterion |
|---|------------|---------------------|
| D1 | LangGraph state machine (9 stages) | State transitions traced in LangSmith; no infinite loops |
| D2 | Intent extraction | Given a 20-page BRD, extracts bounded contexts, integrations, NFRs in < 30 seconds |
| D3 | Standards consultation | Retrieves relevant skills/specs/instructions; records artifact hashes in Ledger |
| D4 | LiteLLM gateway integration | Routes to correct provider based on task tier; fallback works |
| D5 | Architecture proposal generator | Produces draw.io XML + component list + OpenAPI stubs |
| D6 | Agent context assembler | Packages work bundle for each specialist agent |
| D7 | Temporal.io workflow | Long-running orchestration survives Portal restart; resumes from last checkpoint |
| D8 | Cost tracker | Per-orchestration cost visible in Portal UI and Pipeline Ledger |
| D9 | Ledger integration | Every state machine transition = Ledger event with artifact hashes |
| D10 | Evaluation harness | ≥3 golden projects; harness runs on every commit; reports pass/fail |

---

## LangGraph State Machine Design

```python
from langgraph.graph import StateGraph, END
from typing import TypedDict, Annotated
import operator

class OrchestrationState(TypedDict):
    project_id: str
    stage: int
    intent: dict                    # Extracted from BRD/HLD/ICD
    context_bundle: dict            # Skills/specs/instructions retrieved
    proposal: dict                  # Architecture proposal artifact
    proposal_version: str           # e.g., "0.1", "0.2"
    review_status: str              # pending, approved, changes-requested, rejected
    review_comments: list[dict]
    delegation_plan: list[dict]     # Work packages for specialist agents
    agent_results: Annotated[list, operator.add]   # Accumulated agent outputs
    cost_tracker: dict              # LLM tokens and costs
    errors: list[str]

# State machine nodes
def intent_extraction_node(state: OrchestrationState) -> dict:
    """Stage 1+2: Upload documents → extract intent."""
    ...

def standards_consultation_node(state: OrchestrationState) -> dict:
    """Stage 3: Query capability fabric for relevant skills/specs."""
    ...

def proposal_generation_node(state: OrchestrationState) -> dict:
    """Stage 4: Generate architecture proposal artifacts."""
    ...

def review_gate_node(state: OrchestrationState) -> str:
    """Stage 5: Check review status → route to approved/changes/rejected."""
    if state["review_status"] == "approved":
        return "delegate"
    elif state["review_status"] == "changes-requested":
        return "revise"
    elif state["review_status"] == "rejected":
        return END
    else:
        return "wait_for_review"  # Human in the loop

def revision_node(state: OrchestrationState) -> dict:
    """Apply review comments and regenerate proposal."""
    ...

def delegation_node(state: OrchestrationState) -> dict:
    """Stage 6: Break approved plan into specialist agent work packages."""
    ...

def parallel_execution_node(state: OrchestrationState) -> dict:
    """Stage 7: Invoke specialist agents in parallel where dependencies allow."""
    ...

def verification_node(state: OrchestrationState) -> dict:
    """Stage 8: Run deployed-system verification via Integration Test Agent."""
    ...

def handover_node(state: OrchestrationState) -> dict:
    """Stage 9: Package handover bundle; register in Project Registry."""
    ...

# Build the graph
graph = StateGraph(OrchestrationState)
graph.add_node("intent_extraction", intent_extraction_node)
graph.add_node("standards_consultation", standards_consultation_node)
graph.add_node("proposal_generation", proposal_generation_node)
graph.add_node("review_gate", review_gate_node)
graph.add_node("revision", revision_node)
graph.add_node("delegation", delegation_node)
graph.add_node("parallel_execution", parallel_execution_node)
graph.add_node("verification", verification_node)
graph.add_node("handover", handover_node)

graph.set_entry_point("intent_extraction")
graph.add_edge("intent_extraction", "standards_consultation")
graph.add_edge("standards_consultation", "proposal_generation")
graph.add_edge("proposal_generation", "review_gate")
graph.add_conditional_edges("review_gate", lambda s: s,
    {"delegate": "delegation", "revise": "revision",
     "wait_for_review": "review_gate", END: END})
graph.add_edge("revision", "review_gate")
graph.add_edge("delegation", "parallel_execution")
graph.add_edge("parallel_execution", "verification")
graph.add_edge("verification", "handover")
graph.add_edge("handover", END)

orchestration_graph = graph.compile(checkpointer=postgres_checkpointer)
```

---

## Intent Extraction

The intent extractor uses a structured LLM call (Claude Sonnet via LiteLLM) with a JSON output schema:

```python
INTENT_EXTRACTION_SCHEMA = {
    "bounded_contexts": [
        { "name": str, "description": str, "responsibilities": list[str] }
    ],
    "integrations": [
        { "system": str, "direction": "inbound|outbound|bidirectional",
          "purpose": str, "protocol": str }
    ],
    "users_and_roles": [
        { "role": str, "count_estimate": str, "key_workflows": list[str] }
    ],
    "non_functional_requirements": {
        "availability": str,
        "performance": str,
        "data_residency": str,
        "compliance": list[str],
        "scale_estimate": str
    },
    "technology_preferences": list[str],
    "constraints": list[str],
    "open_questions": list[str]
}

async def extract_intent(documents: list[bytes]) -> dict:
    text = await pdf_extractor.extract_all(documents)
    response = await litellm_client.completion(
        model="claude-sonnet-4-5",  # Premium tier for intent extraction
        messages=[
            {"role": "system", "content": INTENT_EXTRACTION_SYSTEM_PROMPT},
            {"role": "user", "content": f"Extract intent from these documents:\n\n{text}"}
        ],
        response_format={"type": "json_object", "schema": INTENT_EXTRACTION_SCHEMA}
    )
    return json.loads(response.choices[0].message.content)
```

---

## Standards Consultation

```python
async def consult_standards(intent: dict) -> dict:
    """
    Given extracted intent, retrieve the most relevant skills, specs, and instructions
    from the Capability Fabric.
    """
    relevant_skills = []
    relevant_specs = []
    relevant_instructions = []

    # Determine relevant tags from intent
    tags = derive_tags_from_intent(intent)

    # Query Fabric API
    skills = await fabric_api.list_skills(tags=tags)
    for skill in skills[:10]:  # Top 10 by relevance score
        full_skill = await fabric_api.get_skill(skill["id"])
        relevant_skills.append(full_skill)
        # Record in Ledger: which skill version was consulted
        await ledger.record(LedgerEvent(
            event_type="portal.stage.standards-consulted",
            data={"skill_id": skill["id"], "version": skill["version"],
                  "content_hash": skill["content_hash"]}
        ))

    return {
        "skills": relevant_skills,
        "specs": relevant_specs,
        "instructions": relevant_instructions,
        "bundle_hash": compute_bundle_hash(relevant_skills + relevant_specs + relevant_instructions)
    }
```

---

## LiteLLM Gateway Configuration

```yaml
# litellm-config.yaml
model_list:
  - model_name: "premium"
    litellm_params:
      model: "anthropic/claude-sonnet-4-5"
      api_key: "os.environ/ANTHROPIC_API_KEY"
      max_tokens: 8192
    model_info:
      cost_per_1k_input_tokens: 0.003
      cost_per_1k_output_tokens: 0.015
      tier: "premium"

  - model_name: "standard"
    litellm_params:
      model: "azure/gpt-4o"
      api_base: "os.environ/AZURE_OPENAI_ENDPOINT"
      api_key: "os.environ/AZURE_OPENAI_API_KEY"
    model_info:
      tier: "standard"

  - model_name: "economy"
    litellm_params:
      model: "deepseek/deepseek-v3"
      api_key: "os.environ/DEEPSEEK_API_KEY"
    model_info:
      tier: "economy"

# Routing rules
routing_strategy: "cost-based"  # fallback to cheapest available
fallbacks:
  - ["premium", "standard"]
  - ["standard", "economy"]

# Budget enforcement (pre-hook fires if exceeded)
budget_manager:
  max_budget_per_project: 50.0   # USD per orchestration cycle
  budget_duration: "1d"
```

---

## Temporal.io Workflow

For long-running orchestrations (which can take hours for large projects), Temporal ensures the workflow survives restarts:

```python
@workflow.defn
class ProjectOrchestrationWorkflow:
    @workflow.run
    async def run(self, project_id: str, document_uris: list[str]) -> dict:
        intent = await workflow.execute_activity(
            extract_intent_activity,
            args=[document_uris],
            schedule_to_close_timeout=timedelta(minutes=5)
        )

        context_bundle = await workflow.execute_activity(
            consult_standards_activity,
            args=[intent],
            schedule_to_close_timeout=timedelta(minutes=2)
        )

        proposal = await workflow.execute_activity(
            generate_proposal_activity,
            args=[intent, context_bundle],
            schedule_to_close_timeout=timedelta(minutes=10)
        )

        # Wait for human review (up to 5 business days)
        review_signal = await workflow.wait_for_signal_with_timeout(
            "review-completed", timeout=timedelta(days=5)
        )

        if review_signal.decision == "rejected":
            return {"status": "rejected"}

        # Parallel specialist agent execution
        agent_results = await asyncio.gather(
            workflow.execute_child_workflow(BackendAgentWorkflow, args=[...]),
            workflow.execute_child_workflow(FrontendAgentWorkflow, args=[...]),
            workflow.execute_child_workflow(DevOpsAgentWorkflow, args=[...]),
            return_exceptions=True
        )

        return await workflow.execute_activity(
            handover_activity, args=[project_id, agent_results]
        )
```

---

## Evaluation Harness

The evaluation harness validates the orchestrator against known-good historical AD Ports projects:

```python
# Golden test cases
GOLDEN_PROJECTS = [
    {
        "name": "jul-dgd-simple",
        "brd_path": "tests/golden/jul-dgd-simple/brd.pdf",
        "expected_bounded_contexts": ["DGD Submission", "Fee Calculation", "Document Management"],
        "expected_integrations": ["SINTECE", "MPay"],
        "expected_pattern": "angular-mfe-dotnet-cqrs-postgres",
        "min_quality_score": 0.75
    },
    # ... more golden projects
]

async def run_harness():
    results = []
    for project in GOLDEN_PROJECTS:
        result = await run_orchestrator_against(project)
        score = evaluate_result(result, project)
        results.append({"project": project["name"], "score": score, "passed": score >= project["min_quality_score"]})
    return results

def evaluate_result(result: dict, expected: dict) -> float:
    scores = []
    # Bounded context overlap
    bc_overlap = len(set(result["bounded_contexts"]) & set(expected["expected_bounded_contexts"]))
    scores.append(bc_overlap / len(expected["expected_bounded_contexts"]))
    # Integration detection
    int_overlap = len(set(result["integrations"]) & set(expected["expected_integrations"]))
    scores.append(int_overlap / len(expected["expected_integrations"]))
    # Pattern selection
    scores.append(1.0 if result["pattern"] == expected["expected_pattern"] else 0.0)
    # Build + test pass rate (deferred to Phase 12+)
    return sum(scores) / len(scores)
```

---

## Step-by-Step Execution Plan

### Week 1: LangGraph + Intent Extraction

- [ ] Set up LangGraph and LiteLLM in the agents service.
- [ ] Implement `intent_extraction_node` with PDF text extraction.
- [ ] Implement `standards_consultation_node`.
- [ ] Deploy LiteLLM gateway to AKS.
- [ ] Unit test intent extraction against 3 synthetic BRDs.

### Week 2: Proposal Generation + Review Gate

- [ ] Implement `proposal_generation_node` (draw.io XML + component decomposition).
- [ ] Implement `review_gate_node` with human-in-the-loop wait.
- [ ] Implement `revision_node` (apply comments, regenerate).
- [ ] Wire review gate to Portal API approval webhook.
- [ ] Integration test: submit BRD → receive proposal → approve → advance.

### Week 3: Delegation + Temporal.io

- [ ] Implement `delegation_node` (break plan into specialist agent work packages).
- [ ] Implement parallel execution stub (invoke specialist agent stubs from Phase 12+).
- [ ] Set up Temporal.io server on AKS.
- [ ] Wrap LangGraph workflow in Temporal.io workflow.
- [ ] Integration test: workflow survives orchestrator restart mid-execution.

### Week 4: Cost Tracking + Ledger + Evaluation

- [ ] Implement per-orchestration cost tracking (LangSmith + Portal cost dashboard).
- [ ] Wire all state machine transitions to Pipeline Ledger.
- [ ] Build evaluation harness (3 golden projects).
- [ ] Run harness: target ≥75% pass rate on first run.
- [ ] Fix top failures; re-run until ≥75%.

---

## Gate Criterion (Gate 1 Prerequisite)

- All 10 deliverables pass acceptance criteria.
- Evaluation harness: ≥75% pass rate across 3 golden projects.
- Full orchestration from BRD upload to architecture proposal < 5 minutes.
- Temporal.io workflow survives a mid-orchestration Portal restart and resumes.
- Per-orchestration cost tracked; LLM budget hook fires when limit exceeded.
- LangSmith traces visible for every orchestration run.

---

*Phase 10 — Orchestration Agent Core — AI Portal — v1.0*
