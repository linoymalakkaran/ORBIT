"""Ticket Implementation Agent — takes a JIRA/ADO ticket and produces a complete code change
implementing that story end-to-end (backend + frontend + migration + tests + PR)."""
from __future__ import annotations

import logging
from typing import Annotated, Optional, TypedDict
import operator

import httpx
import litellm
from fastapi import FastAPI, HTTPException
from langgraph.graph import END, StateGraph
from opentelemetry.instrumentation.fastapi import FastAPIInstrumentor
from pydantic import BaseModel
from pydantic_settings import BaseSettings, SettingsConfigDict

logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO)


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_prefix="TICKET_", env_file=".env", extra="ignore")
    litellm_api_base: str = "http://litellm-gateway.litellm.svc:4000"
    litellm_api_key: str = "changeme"
    default_model: str = "gpt-4o"
    backend_agent_url: str = "http://backend-specialist-agent.ai-portal.svc:80"
    frontend_agent_url: str = "http://frontend-specialist-agent.ai-portal.svc:80"
    database_agent_url: str = "http://database-agent.ai-portal.svc:80"
    qa_agent_url: str = "http://qa-agent.ai-portal.svc:80"
    gitlab_mcp_url: str = "http://mcp-registry.ai-portal.svc:80"
    jira_mcp_url: str = "http://jira-mcp.ai-portal.svc:80"
    ado_mcp_url: str = "http://ado-mcp.ai-portal.svc:80"
    ledger_url: str = "http://pipeline-ledger.ai-portal.svc:80"
    pr_review_url: str = "http://pr-review-agent.ai-portal.svc:80"


settings = Settings()
litellm.api_base = settings.litellm_api_base
litellm.api_key = settings.litellm_api_key


class TicketImplState(TypedDict):
    project_id: str
    ticket_id: str                          # JIRA ticket key e.g. "ORBIT-123"
    ticket_title: str
    acceptance_criteria: list[str]
    openapi_stub: str
    service_name: str
    domain_entities_code: str
    cqrs_handlers_code: str
    migration_sql: str
    angular_component_code: str
    test_code: str
    branch_name: str
    pr_url: Optional[str]
    pr_review: Optional[dict]
    implementation_notes: Annotated[list[str], operator.add]
    # G20: source ticket references for transition
    jira_ticket_id: Optional[str]           # e.g. "ORBIT-123" (Jira)
    ado_work_item_id: Optional[int]         # e.g. 4521 (Azure DevOps)


async def _llm(prompt: str, system: str = "You are a senior full-stack engineer.") -> str:
    r = await litellm.acompletion(
        model=settings.default_model,
        messages=[{"role": "system", "content": system}, {"role": "user", "content": prompt}],
        temperature=0.05,
    )
    return r.choices[0].message.content or ""


async def analyse_ticket(state: TicketImplState) -> dict:
    """Analyse the ticket and determine which layers need changes."""
    prompt = f"""Analyse JIRA ticket '{state['ticket_id']}: {state['ticket_title']}'.

Acceptance criteria:
{chr(10).join(f'- {c}' for c in state['acceptance_criteria'])}

OpenAPI context:
{state['openapi_stub'][:1000]}

Determine:
1. What .NET entities/handlers need to be created or modified
2. What database changes are needed
3. What Angular components need to be created or modified
4. What tests are needed

Output a brief implementation plan (bullet points)."""
    plan = await _llm(prompt)
    return {"implementation_notes": [f"Implementation plan:\n{plan}"]}


async def generate_backend_changes(state: TicketImplState) -> dict:
    """Generate .NET CQRS changes for this ticket."""
    prompt = f"""Generate .NET 9 CQRS implementation for ticket: '{state['ticket_title']}'.

Acceptance criteria:
{chr(10).join(f'- {c}' for c in state['acceptance_criteria'])}

Service: {state['service_name']}
Existing context: {state['openapi_stub'][:800]}

Generate:
1. New domain entity or extension (if needed)
2. Command + CommandHandler (if creates/updates data)
3. Query + QueryHandler (if retrieves data)
4. FluentValidation validator
5. Controller action(s)

Use namespace {state['service_name']}.Application.

Output ONLY C# code with proper namespaces and XML doc comments."""
    code = await _llm(prompt)
    return {"cqrs_handlers_code": code, "implementation_notes": [f"Backend code generated for ticket {state['ticket_id']}"]}


async def generate_migration(state: TicketImplState) -> dict:
    """Generate DB migration if ticket requires schema changes."""
    prompt = f"""Generate EF Core migration and SQL for ticket: '{state['ticket_title']}'.

Acceptance criteria:
{chr(10).join(f'- {c}' for c in state['acceptance_criteria'][:5])}

Determine if a migration is needed. If yes, generate:
- EF Core Migration class (Up/Down)
- Equivalent SQL

If no migration needed, output: '-- No migration required'"""
    sql = await _llm(prompt)
    return {"migration_sql": sql}


async def generate_frontend_changes(state: TicketImplState) -> dict:
    """Generate Angular component changes for this ticket."""
    prompt = f"""Generate Angular 20 component changes for ticket: '{state['ticket_title']}'.

Acceptance criteria:
{chr(10).join(f'- {c}' for c in state['acceptance_criteria'][:5])}

Service: {state['service_name']}
OpenAPI context: {state['openapi_stub'][:500]}

Generate:
1. Angular standalone component TypeScript (PrimeNG + Tailwind)
2. Component template (HTML)
3. NgRx action/reducer/effect if state management needed
4. Service method call to backend API
5. i18n keys (en + ar)

Output TypeScript + HTML code."""
    code = await _llm(prompt)
    return {"angular_component_code": code, "implementation_notes": [f"Frontend code generated for ticket {state['ticket_id']}"]}


async def generate_tests(state: TicketImplState) -> dict:
    """Generate unit + integration tests for the ticket changes."""
    prompt = f"""Generate tests for ticket: '{state['ticket_title']}'.

Acceptance criteria (these become test cases):
{chr(10).join(f'- {c}' for c in state['acceptance_criteria'])}

Generate:
1. xUnit test for each acceptance criterion (C#)
2. Jest test for Angular component
3. Playwright E2E test scenario

Output code for all three layers."""
    code = await _llm(prompt)
    return {"test_code": code}


async def create_branch_and_pr(state: TicketImplState) -> dict:
    """Create a GitLab branch with the generated code and open an MR."""
    ticket_safe = state["ticket_id"].lower().replace(" ", "-")
    branch = f"feat/{ticket_safe}-implementation"

    # Call GitLab MCP to create branch
    try:
        async with httpx.AsyncClient(timeout=15) as client:
            resp = await client.post(f"{settings.gitlab_mcp_url}/invoke/gitlab-mcp", json={
                "tool": "create_branch",
                "params": {"name": branch, "ref": "main"},
            })
            if resp.status_code == 200:
                # Create MR
                mr_resp = await client.post(f"{settings.gitlab_mcp_url}/invoke/gitlab-mcp", json={
                    "tool": "create_merge_request",
                    "params": {
                        "title": f"feat: {state['ticket_title']}",
                        "description": f"Implements {state['ticket_id']}\n\n## Acceptance Criteria\n" + "\n".join(f"- [ ] {c}" for c in state["acceptance_criteria"]),
                        "source_branch": branch,
                        "target_branch": "main",
                        "labels": ["AI-generated", state["ticket_id"]],
                    },
                })
                pr_url = mr_resp.json().get("result", {}).get("web_url", "")
            else:
                pr_url = f"https://gitlab.ai.adports.ae/orbit/{state['service_name'].lower()}/-/merge_requests/new?branch={branch}"
    except Exception as e:
        pr_url = f"branch:{branch} (MCP error: {e})"

    # G20: Transition source ticket to "In Review" after PR is created
    if pr_url and not pr_url.startswith("branch:"):
        await _transition_ticket(state)

    return {"branch_name": branch, "pr_url": pr_url}


async def _transition_ticket(state: TicketImplState) -> None:
    """Phase 22 – G20: Transitions the source Jira/ADO ticket to 'In Review'."""
    try:
        async with httpx.AsyncClient(timeout=10) as client:
            if state.get("jira_ticket_id"):
                resp = await client.post(
                    f"{settings.jira_mcp_url}/tools/transition_issue",
                    json={"issue_key": state["jira_ticket_id"], "transition": "In Review"},
                )
                if resp.status_code == 200:
                    logger.info("Transitioned Jira ticket %s to 'In Review'", state["jira_ticket_id"])
                else:
                    logger.warning("Jira transition returned %d for %s", resp.status_code, state["jira_ticket_id"])

            if state.get("ado_work_item_id"):
                resp = await client.post(
                    f"{settings.ado_mcp_url}/tools/transition_work_item",
                    json={"project": state["project_id"], "work_item_id": state["ado_work_item_id"], "state": "In Review"},
                )
                if resp.status_code == 200:
                    logger.info("Transitioned ADO work item %d to 'In Review'", state["ado_work_item_id"])
                else:
                    logger.warning("ADO transition returned %d for %d", resp.status_code, state["ado_work_item_id"])
    except Exception as ex:
        logger.warning("Ticket transition failed (non-fatal): %s", ex)


async def auto_review_pr(state: TicketImplState) -> dict:
    """Trigger PR Review Agent on the new MR."""
    if not state.get("pr_url"):
        return {"pr_review": None}
    try:
        async with httpx.AsyncClient(timeout=30) as client:
            resp = await client.post(f"{settings.pr_review_url}/api/reviews", json={
                "project_id": state["project_id"],
                "mr_url": state["pr_url"],
            })
            if resp.status_code == 200:
                return {"pr_review": resp.json()}
    except Exception:
        pass
    return {"pr_review": None}


def _build_graph():
    g = StateGraph(TicketImplState)
    for name, fn in [
        ("analyse_ticket", analyse_ticket),
        ("generate_backend_changes", generate_backend_changes),
        ("generate_migration", generate_migration),
        ("generate_frontend_changes", generate_frontend_changes),
        ("generate_tests", generate_tests),
        ("create_branch_and_pr", create_branch_and_pr),
        ("auto_review_pr", auto_review_pr),
    ]:
        g.add_node(name, fn)
    g.add_edge("analyse_ticket", "generate_backend_changes")
    g.add_edge("generate_backend_changes", "generate_migration")
    g.add_edge("generate_migration", "generate_frontend_changes")
    g.add_edge("generate_frontend_changes", "generate_tests")
    g.add_edge("generate_tests", "create_branch_and_pr")
    g.add_edge("create_branch_and_pr", "auto_review_pr")
    g.add_edge("auto_review_pr", END)
    g.set_entry_point("analyse_ticket")
    return g.compile()


_graph = _build_graph()

app = FastAPI(title="ORBIT Ticket Implementation Agent", version="1.0.0")
FastAPIInstrumentor.instrument_app(app)


class TicketImplRequest(BaseModel):
    project_id: str
    ticket_id: str
    ticket_title: str
    acceptance_criteria: list[str]
    service_name: str
    openapi_stub: str = ""
    # G20: optional source ticket references for transition
    jira_ticket_id: Optional[str] = None   # e.g. "ORBIT-123"
    ado_work_item_id: Optional[int] = None  # e.g. 4521


@app.post("/api/implement/ticket")
async def implement_ticket(req: TicketImplRequest):
    """Implement a ticket end-to-end: backend + migration + frontend + tests + PR."""
    initial: TicketImplState = {
        "project_id": req.project_id,
        "ticket_id": req.ticket_id,
        "ticket_title": req.ticket_title,
        "acceptance_criteria": req.acceptance_criteria,
        "openapi_stub": req.openapi_stub,
        "service_name": req.service_name,
        "domain_entities_code": "",
        "cqrs_handlers_code": "",
        "migration_sql": "",
        "angular_component_code": "",
        "test_code": "",
        "branch_name": "",
        "pr_url": None,
        "pr_review": None,
        "implementation_notes": [],
        "jira_ticket_id": req.jira_ticket_id,
        "ado_work_item_id": req.ado_work_item_id,
    }
    result = await _graph.ainvoke(initial)
    try:
        async with httpx.AsyncClient(timeout=5) as client:
            await client.post(f"{settings.ledger_url}/api/ledger", json={
                "project_id": req.project_id,
                "pipeline_run_id": f"ticket-impl-{req.ticket_id}",
                "stage": "ticket_implementation",
                "actor": "ticket-agent",
                "status": "success",
                "metadata": {"ticket_id": req.ticket_id, "pr_url": result.get("pr_url")},
            })
    except Exception:
        pass
    return {
        "project_id": result["project_id"],
        "ticket_id": result["ticket_id"],
        "branch_name": result["branch_name"],
        "pr_url": result["pr_url"],
        "pr_review": result["pr_review"],
        "artifacts": {
            "cqrs_handlers": result["cqrs_handlers_code"],
            "migration_sql": result["migration_sql"],
            "angular_component": result["angular_component_code"],
            "tests": result["test_code"],
        },
        "implementation_notes": result["implementation_notes"],
    }


@app.get("/health/live")
async def liveness():
    return {"status": "ok"}


@app.get("/health/ready")
async def readiness():
    return {"status": "ok"}
