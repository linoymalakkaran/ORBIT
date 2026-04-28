# Workflow: Ticket Implementation

## Workflow ID
`ticket-implementation`

## Used By
Phase 22 — Ticket Implementation Agent

## Description
Defines the end-to-end workflow for implementing a single Jira / Azure DevOps user story ticket fully automatically: reading the ticket, delegating to specialist agents, assembling generated artefacts into a single PR, and transitioning the ticket to "In Review". This workflow is opt-in per ticket (developer must add the `ai-implement` label).

---

## State Definition

```python
# agents/ticket_implementation/state.py
from typing import TypedDict, Literal


class TicketImplementationState(TypedDict):
    # Input
    ticket_id:             str           # Jira or ADO ticket ID
    ticket_system:         Literal["jira", "ado"]
    project_id:            str           # Portal project registry ID
    
    # Ticket data
    ticket_title:          str | None
    ticket_description:    str | None
    acceptance_criteria:   list[dict] | None
    labels:                list[str]
    story_points:          int | None
    
    # Eligibility
    is_eligible:           bool | None   # Must pass eligibility check
    ineligibility_reason:  str | None
    
    # Architecture context
    architecture_proposal: dict | None   # From Phase 11 ledger entry
    openapi_stubs:         dict | None   # Per-service OpenAPI stubs
    
    # Agent outputs
    database_changes:      dict | None   # From database_agent
    backend_changes:       dict | None   # From backend_agent
    frontend_changes:      dict | None   # From frontend_agent
    test_changes:          dict | None   # From qa_agent
    
    # PR
    branch_name:           str | None
    pr_url:                str | None
    pr_number:             int | None
    pr_review_result:      dict | None   # From PR Review Agent
    
    # Control
    current_step:          str
    error:                 str | None
    cancelled:             bool
    total_cost_cents:      float
```

---

## Eligibility Check

Not all tickets are auto-implementable. The eligibility check runs before any code generation:

```python
# agents/ticket_implementation/nodes/eligibility_check_node.py

ELIGIBLE_STORY_POINT_MAX = 8  # Stories > 8 points are too large for auto-implementation

INELIGIBLE_REASONS = {
    "too_large": "Story points > 8. Split the story before auto-implementation.",
    "no_acceptance_criteria": "Story has no acceptance criteria. Add AC before requesting auto-implementation.",
    "blocked": "Story has unresolved blockers. Resolve dependencies first.",
    "missing_architecture": "No approved architecture proposal found in Pipeline Ledger for this project.",
    "missing_openapi": "No OpenAPI stubs found. Architecture Agent must run first.",
    "production_tier": "Auto-implementation disabled for CRITICAL-tier projects (MPay, DGD) without explicit override.",
    "label_not_set": "Ticket does not have the 'ai-implement' label — opt-in required.",
}


async def eligibility_check_node(state: TicketImplementationState) -> dict:
    """Gate check — abort early if ticket is not suitable for auto-implementation."""
    
    ticket = state["acceptance_criteria"]
    points = state["story_points"] or 0
    
    # Rule 1: Must have 'ai-implement' label
    if "ai-implement" not in state["labels"]:
        return { "is_eligible": False, "ineligibility_reason": INELIGIBLE_REASONS["label_not_set"] }
    
    # Rule 2: Must have acceptance criteria
    if not ticket or len(ticket) == 0:
        return { "is_eligible": False, "ineligibility_reason": INELIGIBLE_REASONS["no_acceptance_criteria"] }
    
    # Rule 3: Story points cap
    if points > ELIGIBLE_STORY_POINT_MAX:
        return { "is_eligible": False, "ineligibility_reason": INELIGIBLE_REASONS["too_large"] }
    
    # Rule 4: Must have approved architecture in Ledger
    arch = await ledger_client.get_approved_architecture(state["project_id"])
    if not arch:
        return { "is_eligible": False, "ineligibility_reason": INELIGIBLE_REASONS["missing_architecture"] }
    
    # Rule 5: Production-critical projects require explicit override flag
    project = await registry_client.get_project(state["project_id"])
    if project["asset_criticality"] == "CRITICAL" and "ai-implement-critical" not in state["labels"]:
        return { "is_eligible": False, "ineligibility_reason": INELIGIBLE_REASONS["production_tier"] }
    
    return {
        "is_eligible": True,
        "architecture_proposal": arch,
        "openapi_stubs": arch.get("openapi_stubs"),
    }
```

---

## LangGraph State Machine

```python
# agents/ticket_implementation/graph.py
from langgraph.graph import StateGraph, END
from .state import TicketImplementationState
from .nodes import (
    fetch_ticket_node,
    eligibility_check_node,
    fetch_architecture_context_node,
    delegate_database_agent_node,
    delegate_backend_agent_node,
    delegate_frontend_agent_node,
    delegate_qa_agent_node,
    assemble_pr_node,
    invoke_pr_review_agent_node,
    transition_ticket_node,
    notify_developer_node,
)


def is_eligible(state: TicketImplementationState) -> str:
    if state["is_eligible"]:
        return "fetch_architecture_context"
    return "notify_developer"    # Notify developer why ticket was skipped


def should_generate_frontend(state: TicketImplementationState) -> str:
    """Only generate frontend if the ticket involves UI changes."""
    labels = state.get("labels", [])
    if "frontend" in labels or "ui" in labels:
        return "delegate_frontend_agent"
    return "delegate_qa_agent"


def graph() -> StateGraph:
    g = StateGraph(TicketImplementationState)

    # Nodes
    g.add_node("fetch_ticket",                fetch_ticket_node)
    g.add_node("eligibility_check",           eligibility_check_node)
    g.add_node("fetch_architecture_context",  fetch_architecture_context_node)
    g.add_node("delegate_database_agent",     delegate_database_agent_node)
    g.add_node("delegate_backend_agent",      delegate_backend_agent_node)
    g.add_node("delegate_frontend_agent",     delegate_frontend_agent_node)
    g.add_node("delegate_qa_agent",           delegate_qa_agent_node)
    g.add_node("assemble_pr",                 assemble_pr_node)
    g.add_node("invoke_pr_review_agent",      invoke_pr_review_agent_node)
    g.add_node("transition_ticket",           transition_ticket_node)
    g.add_node("notify_developer",            notify_developer_node)

    # Entry
    g.set_entry_point("fetch_ticket")

    # Edges
    g.add_edge("fetch_ticket", "eligibility_check")
    g.add_conditional_edges("eligibility_check", is_eligible)
    g.add_edge("fetch_architecture_context", "delegate_database_agent")
    g.add_edge("delegate_database_agent", "delegate_backend_agent")
    g.add_conditional_edges("delegate_backend_agent", should_generate_frontend)
    g.add_edge("delegate_frontend_agent", "delegate_qa_agent")
    g.add_edge("delegate_qa_agent", "assemble_pr")
    g.add_edge("assemble_pr", "invoke_pr_review_agent")
    g.add_edge("invoke_pr_review_agent", "transition_ticket")
    g.add_edge("transition_ticket", "notify_developer")
    g.add_edge("notify_developer", END)

    return g.compile()
```

---

## PR Assembly Node

```python
# agents/ticket_implementation/nodes/assemble_pr_node.py

async def assemble_pr_node(state: TicketImplementationState) -> dict:
    """
    Merge all agent outputs into a single Git branch and open a PR.
    
    Branch naming: ticket/{TICKET_ID}-{ticket-title-slug}
    """
    import slugify

    ticket_slug = slugify.slugify(state["ticket_title"], max_length=50)
    branch = f"ticket/{state['ticket_id']}-{ticket_slug}"

    # Collect all file changes from agents
    all_changes: list[FileChange] = []
    for agent_key in ["database_changes", "backend_changes", "frontend_changes", "test_changes"]:
        changes = state.get(agent_key)
        if changes:
            all_changes.extend(changes.get("files", []))

    # Create branch + commit via GitLab MCP
    await gitlab_mcp.create_branch(state["project_id"], branch)
    await gitlab_mcp.commit_files(
        project_id=state["project_id"],
        branch=branch,
        files=all_changes,
        message=f"feat({state['ticket_id']}): {state['ticket_title']}\n\nAuto-implemented by AD Ports Ticket Implementation Agent.\nTicket: {state['ticket_id']}\nStory Points: {state['story_points']}",
    )

    # Open PR
    pr = await gitlab_mcp.create_merge_request(
        project_id=state["project_id"],
        source_branch=branch,
        target_branch="main",
        title=f"[{state['ticket_id']}] {state['ticket_title']}",
        description=generate_pr_description(state),
        labels=["ai-generated", "needs-review", state["ticket_id"]],
    )

    await ledger_client.record_stage(
        project_id=state["project_id"],
        stage="ticket_implementation.pr_opened",
        output_summary=f"PR #{pr['number']}: {pr['url']}",
    )

    return { "branch_name": branch, "pr_url": pr["url"], "pr_number": pr["number"] }


def generate_pr_description(state: TicketImplementationState) -> str:
    return f"""
## Ticket: [{state['ticket_id']}]({state.get('ticket_url', '#')})

**Story:** {state['ticket_title']}

## Changes Generated

{chr(10).join(f"- **{k.replace('_changes', '').replace('_', ' ').title()}**: {len(state.get(k, {}).get('files', []))} files changed" for k in ['database_changes', 'backend_changes', 'frontend_changes', 'test_changes'] if state.get(k))}

## Acceptance Criteria Coverage

{chr(10).join(f"- [ ] {ac['criterion']}" for ac in (state.get('acceptance_criteria') or []))}

## PR Review

This PR has been automatically reviewed by the AD Ports PR Review Agent.
Review score: {state.get('pr_review_result', {}).get('score', 'Pending')}

> ⚠️ **This code was auto-generated.** Please review carefully before merging.
> All changes have been recorded in the [Pipeline Ledger](https://portal.adports.ae/ledger).
""".strip()
```

---

## Ticket Transition Node

```python
async def transition_ticket_node(state: TicketImplementationState) -> dict:
    """Transition Jira/ADO ticket to 'In Review' and add PR link as comment."""
    
    if state["ticket_system"] == "jira":
        await jira_mcp.add_comment(
            ticket_id=state["ticket_id"],
            comment=f"🤖 **AI Portal Auto-Implementation Complete**\n\nPR opened: {state['pr_url']}\n\nMoving to In Review.",
        )
        await jira_mcp.transition(state["ticket_id"], "In Review")
    else:
        await ado_mcp.update_work_item(
            work_item_id=state["ticket_id"],
            state="In Review",
            comment=f"AI Portal PR: {state['pr_url']}",
        )
    
    return { "current_step": "completed" }
```

---

## Acceptance Criteria

| # | Criterion |
|---|-----------|
| AC1 | Eligibility check runs in < 10 seconds; ineligible tickets produce a human-readable rejection reason |
| AC2 | Branch name follows `ticket/{TICKET_ID}-{slug}` format |
| AC3 | PR description lists acceptance criteria as checkboxes |
| AC4 | PR is auto-reviewed by PR Review Agent before ticket transition |
| AC5 | Ticket transitions to "In Review" only after PR is opened (not before) |
| AC6 | Developer notified via Teams/Slack with PR link and review score |
| AC7 | All changes recorded in Pipeline Ledger |
| AC8 | Total cost tracked in `total_cost_cents` |
| AC9 | Workflow is idempotent — re-running for same ticket ID skips if PR already exists |
| AC10 | CRITICAL-tier projects blocked unless `ai-implement-critical` label present |

---

*Ticket Implementation Workflow — AD Ports AI Portal — v1.0.0 — Owner: Intelligence Squad*
