"""LangGraph state machine for the ORBIT AI pipeline.

Pipeline stages:
  1  Requirements Analysis
  2  Architecture Design
  3  API Design
  4  Database Schema Design
  5  IaC Generation
  6  CI Pipeline Generation
  7  Code Generation (per-service)
  8  Unit Test Generation
  9  Code Review
  10 Security Scan
  11 Documentation Generation
  12 PR Review & Merge
"""
from __future__ import annotations

from typing import Annotated, Any, TypedDict
import operator
import uuid

from langgraph.graph import StateGraph, END

from app.llm import chat
from app.mcp_client import invoke_mcp_tool


# ── State ────────────────────────────────────────────────────────────────────

class PipelineState(TypedDict):
    project_id: str
    project_name: str
    requirements: str
    stage: int
    messages: Annotated[list[dict], operator.add]
    artifacts: Annotated[list[dict], operator.add]
    errors: Annotated[list[str], operator.add]
    completed: bool


# ── Stage nodes ───────────────────────────────────────────────────────────────

async def requirements_analysis(state: PipelineState) -> dict:
    result = await chat([
        {"role": "system", "content": "You are an expert BA. Analyse requirements and output structured user stories."},
        {"role": "user", "content": f"Project: {state['project_name']}\n\n{state['requirements']}"},
    ])
    return {
        "stage": 2,
        "messages": [{"role": "assistant", "stage": 1, "content": result}],
        "artifacts": [{"type": "requirements_analysis", "stage": 1, "content": result}],
    }


async def architecture_design(state: PipelineState) -> dict:
    prior = _last_artifact(state, "requirements_analysis")
    result = await chat([
        {"role": "system", "content": "You are a senior software architect. Design a microservices architecture."},
        {"role": "user", "content": f"User stories:\n{prior}"},
    ])
    return {
        "stage": 3,
        "messages": [{"role": "assistant", "stage": 2, "content": result}],
        "artifacts": [{"type": "architecture_design", "stage": 2, "content": result}],
    }


async def api_design(state: PipelineState) -> dict:
    arch = _last_artifact(state, "architecture_design")
    result = await chat([
        {"role": "system", "content": "Generate OpenAPI 3.1 specifications for all identified services."},
        {"role": "user", "content": arch},
    ])
    return {
        "stage": 4,
        "messages": [{"role": "assistant", "stage": 3, "content": result}],
        "artifacts": [{"type": "api_design", "stage": 3, "content": result}],
    }


async def db_schema_design(state: PipelineState) -> dict:
    arch = _last_artifact(state, "architecture_design")
    result = await chat([
        {"role": "system", "content": "Design normalised PostgreSQL schemas for all services. Output DDL."},
        {"role": "user", "content": arch},
    ])
    return {
        "stage": 5,
        "messages": [{"role": "assistant", "stage": 4, "content": result}],
        "artifacts": [{"type": "db_schema", "stage": 4, "content": result}],
    }


async def iac_generation(state: PipelineState) -> dict:
    arch = _last_artifact(state, "architecture_design")
    result = await chat([
        {"role": "system", "content": "Generate Pulumi TypeScript IaC for TKG Kubernetes deployment."},
        {"role": "user", "content": arch},
    ])
    return {
        "stage": 6,
        "messages": [{"role": "assistant", "stage": 5, "content": result}],
        "artifacts": [{"type": "iac", "stage": 5, "content": result}],
    }


async def ci_pipeline_generation(state: PipelineState) -> dict:
    arch = _last_artifact(state, "architecture_design")
    result = await chat([
        {"role": "system", "content": "Generate a .gitlab-ci.yml pipeline for build, test, and deploy to TKG."},
        {"role": "user", "content": arch},
    ])
    return {
        "stage": 7,
        "messages": [{"role": "assistant", "stage": 6, "content": result}],
        "artifacts": [{"type": "ci_pipeline", "stage": 6, "content": result}],
    }


async def code_generation(state: PipelineState) -> dict:
    api = _last_artifact(state, "api_design")
    result = await chat([
        {"role": "system", "content": "Generate production-quality .NET 9 service code from the API spec."},
        {"role": "user", "content": api},
    ])
    return {
        "stage": 8,
        "messages": [{"role": "assistant", "stage": 7, "content": result}],
        "artifacts": [{"type": "source_code", "stage": 7, "content": result}],
    }


async def test_generation(state: PipelineState) -> dict:
    code = _last_artifact(state, "source_code")
    result = await chat([
        {"role": "system", "content": "Generate comprehensive xUnit tests with >80% coverage target."},
        {"role": "user", "content": code},
    ])
    return {
        "stage": 9,
        "messages": [{"role": "assistant", "stage": 8, "content": result}],
        "artifacts": [{"type": "tests", "stage": 8, "content": result}],
    }


async def code_review(state: PipelineState) -> dict:
    code = _last_artifact(state, "source_code")
    result = await chat([
        {"role": "system", "content": "You are a senior code reviewer. Review for correctness, security, performance."},
        {"role": "user", "content": code},
    ])
    return {
        "stage": 10,
        "messages": [{"role": "assistant", "stage": 9, "content": result}],
        "artifacts": [{"type": "code_review", "stage": 9, "content": result}],
    }


async def security_scan(state: PipelineState) -> dict:
    code = _last_artifact(state, "source_code")
    result = await chat([
        {"role": "system", "content": "Perform SAST analysis. Identify OWASP Top-10 vulnerabilities and propose fixes."},
        {"role": "user", "content": code},
    ])
    return {
        "stage": 11,
        "messages": [{"role": "assistant", "stage": 10, "content": result}],
        "artifacts": [{"type": "security_report", "stage": 10, "content": result}],
    }


async def documentation(state: PipelineState) -> dict:
    arch = _last_artifact(state, "architecture_design")
    api  = _last_artifact(state, "api_design")
    result = await chat([
        {"role": "system", "content": "Generate comprehensive technical documentation: README, ADR, runbook."},
        {"role": "user", "content": f"Architecture:\n{arch}\n\nAPI:\n{api}"},
    ])
    return {
        "stage": 12,
        "messages": [{"role": "assistant", "stage": 11, "content": result}],
        "artifacts": [{"type": "documentation", "stage": 11, "content": result}],
    }


async def pr_review(state: PipelineState) -> dict:
    result = await chat([
        {"role": "system", "content": "Summarise the pipeline output and generate a PR description."},
        {"role": "user", "content": f"Project: {state['project_name']}\nArtifacts: {len(state['artifacts'])} generated."},
    ])
    return {
        "stage": 12,
        "completed": True,
        "messages": [{"role": "assistant", "stage": 12, "content": result}],
        "artifacts": [{"type": "pr_description", "stage": 12, "content": result}],
    }


# ── Routing ──────────────────────────────────────────────────────────────────

def _route(state: PipelineState) -> str:
    if state.get("completed"):
        return END
    stage_map = {
        1: "requirements_analysis",
        2: "architecture_design",
        3: "api_design",
        4: "db_schema_design",
        5: "iac_generation",
        6: "ci_pipeline_generation",
        7: "code_generation",
        8: "test_generation",
        9: "code_review",
        10: "security_scan",
        11: "documentation",
        12: "pr_review",
    }
    return stage_map.get(state["stage"], END)


def _last_artifact(state: PipelineState, artifact_type: str) -> str:
    for a in reversed(state.get("artifacts", [])):
        if a.get("type") == artifact_type:
            return a.get("content", "")
    return ""


# ── Graph ─────────────────────────────────────────────────────────────────────

def build_graph() -> StateGraph:
    g = StateGraph(PipelineState)
    for name, fn in [
        ("requirements_analysis", requirements_analysis),
        ("architecture_design",  architecture_design),
        ("api_design",           api_design),
        ("db_schema_design",     db_schema_design),
        ("iac_generation",       iac_generation),
        ("ci_pipeline_generation", ci_pipeline_generation),
        ("code_generation",      code_generation),
        ("test_generation",      test_generation),
        ("code_review",          code_review),
        ("security_scan",        security_scan),
        ("documentation",        documentation),
        ("pr_review",            pr_review),
    ]:
        g.add_node(name, fn)
        g.add_conditional_edges(name, _route)

    g.set_entry_point("requirements_analysis")
    return g
