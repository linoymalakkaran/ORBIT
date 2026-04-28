# Instructions — Phase 10: Orchestration Agent Core (LangGraph + LiteLLM)

> Add this file to your IDE's custom instructions when building the Orchestration Agent in Python.

---

## Context

You are building the **AD Ports AI Portal Orchestration Agent** — a LangGraph state machine backed by Temporal.io for durability and LiteLLM for provider-agnostic LLM routing. The orchestrator is the single entry point for all complex AI-driven project work.

---

## Python Coding Standards

### Project Structure

```
agents/
├── orchestrator/
│   ├── __init__.py
│   ├── graph.py              ← LangGraph state machine definition
│   ├── state.py              ← OrchestrationState TypedDict
│   ├── nodes/
│   │   ├── intent_extraction.py
│   │   ├── standards_consultation.py
│   │   ├── proposal_generation.py
│   │   ├── review_gate.py
│   │   ├── revision.py
│   │   ├── delegation.py
│   │   ├── parallel_execution.py
│   │   ├── verification.py
│   │   └── handover.py
│   ├── temporal/
│   │   ├── workflows.py      ← Temporal workflow definitions
│   │   └── activities.py     ← Temporal activity implementations
│   └── evaluation/
│       ├── harness.py
│       └── golden_projects/
│           └── *.json
├── shared/
│   ├── litellm_client.py     ← LiteLLM gateway wrapper
│   ├── fabric_client.py      ← Capability Fabric API client
│   ├── ledger_client.py      ← Pipeline Ledger recording
│   └── cost_tracker.py       ← Token counting + cost accumulation
└── tests/
    ├── unit/
    └── integration/
```

### Python Style

- Python 3.12+ with full type annotations.
- Use `async/await` throughout — no sync IO in agent nodes.
- Use `pydantic` v2 for all data models (not TypedDict for models shared across services).
- Use `poetry` for dependency management.
- Line length: 100 characters.
- Docstrings on all public functions.

```python
# CORRECT — typed async node
async def intent_extraction_node(state: OrchestrationState) -> dict:
    """
    Extract structured intent from uploaded BRD/HLD/ICD documents.
    
    Args:
        state: Current orchestration state containing document URIs
        
    Returns:
        State update dict with 'intent' key populated
    """
    documents = await document_store.download_all(state["document_uris"])
    text = await pdf_extractor.extract_text(documents)
    
    async with cost_tracker.track("intent_extraction", state["project_id"]):
        intent = await litellm_client.structured_completion(
            task_tier="premium",
            system_prompt=INTENT_EXTRACTION_PROMPT,
            user_message=f"Extract intent:\n\n{text[:50_000]}",  # Safety truncation
            output_schema=IntentSchema
        )
    
    await ledger.record(LedgerEvent(
        project_id=state["project_id"],
        event_type="portal.stage.intent-captured",
        stage_number=2,
        data={"intent_hash": compute_hash(intent.model_dump_json())}
    ))
    
    return {"intent": intent.model_dump(), "stage": 2}
```

---

## LangGraph Rules

- Every node returns a `dict` with only the keys it modifies — do not return the full state.
- Conditional edges return a string key, not the state.
- Always use `checkpointer=postgres_checkpointer` — never run without a checkpointer.
- Never put `async` I/O in conditional edge functions — only in nodes.
- Use `interrupt_before=["review_gate"]` for the human-in-the-loop gate.

```python
# CORRECT — conditional edge returns string
def route_after_review(state: OrchestrationState) -> str:
    status = state["review_status"]
    if status == "approved":
        return "delegation"
    elif status == "changes-requested":
        return "revision"
    elif status == "rejected":
        return END
    else:
        return "__interrupt__"  # Wait for human signal
```

---

## LiteLLM Client Pattern

```python
# shared/litellm_client.py
class LiteLLMClient:
    async def structured_completion(
        self,
        task_tier: Literal["premium", "standard", "economy"],
        system_prompt: str,
        user_message: str,
        output_schema: type[BaseModel],
        project_id: str | None = None
    ) -> BaseModel:
        """Make a structured LLM call with schema validation."""
        # Check project budget before calling
        if project_id:
            await budget_guard.check(project_id, estimated_tokens=len(user_message) // 4)

        response = await litellm.acompletion(
            model=self._select_model(task_tier),
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_message}
            ],
            response_format={"type": "json_object"},
            temperature=0.1  # Low temperature for deterministic outputs
        )

        content = response.choices[0].message.content
        # Track cost
        self.cost_tracker.record(
            project_id=project_id,
            model=response.model,
            input_tokens=response.usage.prompt_tokens,
            output_tokens=response.usage.completion_tokens,
            cost_usd=completion_cost(response)
        )
        return output_schema.model_validate_json(content)
```

---

## Temporal.io Activity Rules

- Activities must be idempotent — they may be retried.
- Activities must not have long-running loops — use sub-workflows for fan-out.
- Activities serialize inputs/outputs as JSON — use Pydantic models.
- Set appropriate timeouts on every activity.

```python
# CORRECT — idempotent activity
@activity.defn
async def generate_proposal_activity(args: ProposalGenerationArgs) -> ProposalResult:
    """Generate architecture proposal. Idempotent: same inputs = same outputs."""
    # Check if already generated (idempotency check)
    existing = await artifact_store.find(args.project_id, "architecture-proposal", args.context_hash)
    if existing:
        return ProposalResult(artifact_uri=existing.uri, artifact_hash=existing.hash, skipped=True)
    # Generate new proposal
    ...
```

---

## Determinism Principle

- 70–80% of orchestration decisions should be **deterministic** (pattern selection, component mapping, dependency analysis).
- Use LLMs **only** for language judgment: intent extraction, ambiguity resolution, rationale generation, code review narrative.
- Never call an LLM to make a binary yes/no decision that can be encoded as a rule.

```python
# WRONG — LLM for a deterministic decision
use_postgres = await llm.complete("Should this project use PostgreSQL?")

# CORRECT — deterministic rule
use_postgres = "relational" in intent["data_requirements"] or \
               any(t in intent["technology_preferences"] for t in ["postgres", "postgresql"])
```

---

## Error Handling

- Catch specific exceptions, not bare `except Exception`.
- On unrecoverable errors, write a `portal.stage.error` Ledger event and raise to Temporal for retry.
- After 3 Temporal retries, escalate to `portal.stage.manual-intervention-required`.

```python
try:
    result = await litellm_client.structured_completion(...)
except litellm.APIError as e:
    logger.error("LLM API error in intent_extraction", error=str(e), project_id=state["project_id"])
    await ledger.record_error(state["project_id"], "intent_extraction", str(e))
    raise  # Temporal retries
except ValidationError as e:
    logger.error("LLM output failed schema validation", errors=e.errors())
    raise
```

---

## What NOT to Do

- Do not use synchronous HTTP calls in node functions — always `await`.
- Do not store large blobs (>10KB) in the LangGraph state — store in Azure Blob and put the URI in state.
- Do not access Vault or Keycloak directly from agent nodes — use the shared service clients.
- Do not put secrets or PII in the LangGraph state — they will be persisted in the checkpointer.
- Do not use `temperature > 0.3` for structured outputs — high temperature causes schema failures.
- Do not write a node that takes > 30 seconds — break into sub-activities.

---

*Phase 10 Instructions — AI Portal — v1.0*
