# Workflow: Orchestration State Machine

## Workflow ID
`orchestration-state-machine`

## Used By
Phase 10 — LangGraph Orchestration Agent

## Description
Defines the 9-stage LangGraph state machine that drives every project from intake to completed proposal. Each stage is a deterministic Python function or an LLM-backed node. This workflow document is the authoritative reference for implementing and extending the Orchestration Agent.

---

## State Definition

```python
class OrchestrationState(TypedDict):
    # Input
    project_id:          str
    raw_request:         str
    brd_document_url:    str | None
    hld_document_url:    str | None

    # Stage outputs
    intent:              Intent | None              # Stage 1 output
    brd:                 BrdDocument | None         # Stage 2 output
    standards:           list[Standard]             # Stage 3 output
    work_packages:       list[WorkPackage]          # Stage 4 output (decomposition)
    proposal:            ArchitectureProposal | None # Stage 5 output
    review_status:       str | None                  # Stage 6 output
    approved_proposal:   ApprovedProposal | None     # Stage 7 output
    execution_results:   list[AgentResult]           # Stage 8 output
    ledger_entries:      list[LedgerEntry]           # Stage 9 output

    # Control
    current_stage:       str
    revision_count:      int
    max_revisions:       int
    error:               str | None
    cancelled:           bool
```

---

## Stage Definitions

### Stage 1: Extract Intent
- **Node**: `extract_intent_node`
- **Type**: LLM (standard tier)
- **Prompt**: `shared/prompts/intent-extraction.md`
- **Input**: `raw_request`
- **Output**: `intent`
- **Determinism**: 0% (pure LLM)
- **On failure**: Retry 2x; then ask user to rephrase

### Stage 2: Read & Parse BRD/HLD
- **Node**: `parse_brd_node`
- **Type**: Deterministic (document parser) + LLM chunking
- **Input**: `brd_document_url` (if provided)
- **Output**: `brd` (structured: epics, acceptance criteria, stakeholders)
- **Determinism**: 80% (parsing) / 20% (ambiguity resolution via LLM)
- **On failure**: Continue with intent only (BRD optional)

### Stage 3: Consult Capability Fabric
- **Node**: `consult_fabric_node`
- **Type**: Deterministic (MCP tool calls)
- **Input**: `intent.domain`, `intent.boundedContexts`
- **Output**: `standards` (applicable skills, specs, instructions, external standards)
- **Determinism**: 100%
- **MCP calls**: `standards.find_applicable`, `skills.list_for_domain`

### Stage 4: Decompose into Work Packages
- **Node**: `decompose_work_node`
- **Type**: LLM (premium tier, Claude)
- **Input**: `intent`, `brd`, `standards`
- **Output**: `work_packages` (list of agent delegations with inputs/outputs/dependencies)
- **Determinism**: 20% (LLM)
- **Prompt**: Inline (not in shared/prompts — uses structured output)

### Stage 5: Generate Proposal
- **Node**: `generate_proposal_node`
- **Type**: LLM (premium tier) + deterministic generators
- **Input**: `intent`, `brd`, `standards`, `work_packages`
- **Output**: `proposal` (architecture doc, draw.io XML, component decomposition, OpenAPI stubs)
- **Determinism**: 60% (generators) / 40% (LLM rationale)
- **Prompt**: `shared/prompts/architecture-proposal.md`

### Stage 6: Human Review Gate
- **Node**: `human_review_node`
- **Type**: Interrupt (Temporal signal wait)
- **Input**: `proposal`
- **Output**: `review_status` (approved | rejected | revision_requested)
- **Determinism**: 100% (just waits for signal)
- **Timeout**: 72 hours (then escalate notification)
- **On revision**: Increment `revision_count`; goto Stage 5 if `revision_count < max_revisions`
- **On max revisions**: Escalate to human architect for manual resolution

### Stage 7: Record Approval in Ledger
- **Node**: `record_approval_node`
- **Type**: Deterministic
- **Input**: `proposal`, `review_status`
- **Output**: `approved_proposal` (with artifact hashes + approver signatures)
- **Determinism**: 100%
- **Ledger event**: `portal.stage.architecture-approved`

### Stage 8: Execute Agent Delegation
- **Node**: `execute_agents_node`
- **Type**: Deterministic dispatcher
- **Input**: `approved_proposal.work_packages`
- **Output**: `execution_results` (one per delegated agent)
- **Determinism**: 100% (dispatcher) — individual agents have their own state machines
- **Note**: Agents run in dependency order; independent agents run in parallel

### Stage 9: Finalize and Record
- **Node**: `finalize_node`
- **Type**: Deterministic
- **Input**: `execution_results`
- **Output**: `ledger_entries` (summary + artifact locations)
- **Determinism**: 100%
- **Ledger event**: `portal.stage.project-generation-completed`

---

## Stage Transition Graph

```
[1: Extract Intent]
        │ ──(low confidence)──► ask for clarification
        ▼
[2: Parse BRD]
        │
        ▼
[3: Consult Fabric]
        │
        ▼
[4: Decompose Work]
        │
        ▼
[5: Generate Proposal] ◄─────────────────────────────┐
        │                                              │ revision (count < max)
        ▼                                              │
[6: Human Review Gate]──(revision_requested)──────────┘
        │
   (approved)
        │
        ▼
[7: Record Approval]
        │
        ▼
[8: Execute Agents]
        │
        ▼
[9: Finalize]
        │
      DONE
```

---

## Temporal.io Durable Workflow

The LangGraph state machine runs inside a Temporal.io workflow for durability:

```python
@workflow.defn
class ProjectOrchestrationWorkflow:
    @workflow.run
    async def run(self, project_id: str) -> OrchestrationResult:
        state = await workflow.execute_activity(
            load_project_state, project_id, schedule_to_close_timeout=timedelta(seconds=30)
        )

        # Run LangGraph state machine with durability
        graph = build_orchestration_graph()
        result = await workflow.execute_activity(
            run_langgraph, state, schedule_to_close_timeout=timedelta(hours=4)
        )

        # Human review gate — waits up to 72 hours
        if result.needs_human_review:
            review_result = await workflow.wait_condition(
                lambda: self._review_signal is not None,
                timeout=timedelta(hours=72)
            )

        return result

    @workflow.signal
    async def submit_review(self, decision: ReviewDecision) -> None:
        self._review_signal = decision
```

---

## Error Recovery

| Error Type | Recovery Strategy |
|------------|-------------------|
| LLM timeout | Retry with same prompt (max 3x) |
| Low confidence intent | Pause workflow; ask user to clarify |
| Agent failure | Record partial result; continue other agents; flag for manual review |
| Human review timeout (72h) | Escalate notification to squad lead + platform admin |
| Budget exceeded | Pause workflow; notify architect; wait for budget approval signal |

---

*shared/workflows/orchestration-state-machine.md — AI Portal — v1.0*
