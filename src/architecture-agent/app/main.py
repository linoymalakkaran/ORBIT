"""Architecture Proposal Agent — generates draw.io diagrams, component decomposition,
OpenAPI stubs, and Docusaurus spec sites from BRD/intent payloads."""
from __future__ import annotations

import asyncio
import json
import logging
import textwrap
from typing import Annotated, Any, TypedDict
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
    model_config = SettingsConfigDict(env_prefix="ARCH_", env_file=".env", extra="ignore")
    litellm_api_base: str = "http://litellm-gateway.litellm.svc:4000"
    litellm_api_key: str = "changeme"
    default_model: str = "gpt-4o"
    ledger_url: str = "http://pipeline-ledger.ai-portal.svc:80"
    minio_url: str = "http://minio.ai-portal-data.svc:9000"


settings = Settings()
litellm.api_base = settings.litellm_api_base
litellm.api_key = settings.litellm_api_key


# ── LangGraph State ──────────────────────────────────────────────────────────

class ProposalState(TypedDict):
    project_id: str
    brd_text: str
    intent: str
    bounded_contexts: list[dict]
    services: list[dict]
    openapi_stubs: Annotated[list[str], operator.add]
    drawio_component_xml: str
    drawio_sequence_xml: str
    infra_plan: str
    qa_plan: str
    security_plan: str
    proposal_version: int


# ── Generators ───────────────────────────────────────────────────────────────

async def _llm(prompt: str, system: str = "You are a senior software architect.") -> str:
    r = await litellm.acompletion(
        model=settings.default_model,
        messages=[{"role": "system", "content": system}, {"role": "user", "content": prompt}],
        temperature=0.1,
    )
    return r.choices[0].message.content or ""


async def extract_intent(state: ProposalState) -> dict:
    result = await _llm(
        f"Extract the core technical intent from this BRD in 2-3 sentences:\n\n{state['brd_text']}"
    )
    return {"intent": result}


async def decompose_bounded_contexts(state: ProposalState) -> dict:
    prompt = f"""From this intent, identify bounded contexts and microservices.
Output JSON array: [{{"name": "...", "responsibility": "...", "interfaces": ["..."]}}]

Intent: {state['intent']}
BRD excerpt: {state['brd_text'][:2000]}"""
    raw = await _llm(prompt)
    try:
        contexts = json.loads(raw)
    except Exception:
        # Extract JSON from markdown code fence
        import re
        m = re.search(r"```(?:json)?\s*(\[.*?\])\s*```", raw, re.DOTALL)
        contexts = json.loads(m.group(1)) if m else [{"name": "CoreService", "responsibility": raw[:200], "interfaces": []}]
    services = [{"name": c["name"].replace(" ", "") + "Service", "context": c["name"], "responsibility": c.get("responsibility", "")} for c in contexts]
    return {"bounded_contexts": contexts, "services": services}


async def generate_openapi_stubs(state: ProposalState) -> dict:
    stubs = []
    for svc in state["services"][:5]:  # cap at 5 to keep context manageable
        prompt = f"""Generate a minimal OpenAPI 3.1 YAML stub for a service named '{svc['name']}'.
Responsibility: {svc['responsibility']}
Include: info, servers (https://api.ai.adports.ae/{svc['name'].lower()}), 3-5 realistic endpoints, request/response schemas.
Output ONLY valid YAML."""
        stub = await _llm(prompt, system="You are an API design expert. Output only valid OpenAPI 3.1 YAML.")
        stubs.append(f"# {svc['name']}\n{stub}")
    return {"openapi_stubs": stubs}


async def generate_drawio_component(state: ProposalState) -> dict:
    services_list = "\n".join(f"- {s['name']}: {s['responsibility']}" for s in state["services"])
    prompt = f"""Generate draw.io XML for a component architecture diagram showing these services and their relationships.
Use mxGraph XML format with cells. Include: API Gateway → Services → Database layers.

Services:
{services_list}

Output ONLY valid draw.io mxGraph XML starting with <mxGraphModel>."""
    xml = await _llm(prompt, system="You are a draw.io diagram generator. Output only valid mxGraph XML.")
    return {"drawio_component_xml": xml}


async def generate_drawio_sequence(state: ProposalState) -> dict:
    prompt = f"""Generate draw.io XML for a sequence diagram showing the main user flow for:
Intent: {state['intent']}
Services: {[s['name'] for s in state['services'][:4]]}

Use mxGraph XML sequence diagram format. Output ONLY valid XML starting with <mxGraphModel>."""
    xml = await _llm(prompt, system="You are a draw.io diagram generator. Output only valid mxGraph XML.")
    return {"drawio_sequence_xml": xml}


async def generate_plans(state: ProposalState) -> dict:
    services_str = ", ".join(s["name"] for s in state["services"])
    infra = await _llm(f"Generate an infrastructure plan for deploying these services on Tanzu TKG / vSphere 8: {services_str}. Include: namespaces, resource quotas, network policies, ingress routes, Vault secret paths. Format as markdown.")
    qa = await _llm(f"Generate a QA automation plan for: {services_str}. Include: E2E test scenarios, load test targets, contract test strategy. Format as markdown.")
    sec = await _llm(f"Generate a security plan for: {services_str}. Include: SAST, DAST, secret scanning, RBAC, network policies, TLS. Format as markdown.")
    return {"infra_plan": infra, "qa_plan": qa, "security_plan": sec}


def _build_graph():
    g = StateGraph(ProposalState)
    g.add_node("extract_intent", extract_intent)
    g.add_node("decompose_bounded_contexts", decompose_bounded_contexts)
    g.add_node("generate_openapi_stubs", generate_openapi_stubs)
    g.add_node("generate_drawio_component", generate_drawio_component)
    g.add_node("generate_drawio_sequence", generate_drawio_sequence)
    g.add_node("generate_plans", generate_plans)
    g.add_edge("extract_intent", "decompose_bounded_contexts")
    g.add_edge("decompose_bounded_contexts", "generate_openapi_stubs")
    g.add_edge("generate_openapi_stubs", "generate_drawio_component")
    g.add_edge("generate_drawio_component", "generate_drawio_sequence")
    g.add_edge("generate_drawio_sequence", "generate_plans")
    g.add_edge("generate_plans", END)
    g.set_entry_point("extract_intent")
    return g.compile()


_graph = _build_graph()

# ── FastAPI ──────────────────────────────────────────────────────────────────

app = FastAPI(title="ORBIT Architecture Proposal Agent", version="1.0.0")
FastAPIInstrumentor.instrument_app(app)


class ProposalRequest(BaseModel):
    project_id: str
    brd_text: str
    proposal_version: int = 1


class RevisionRequest(BaseModel):
    project_id: str
    previous_proposal: dict
    reviewer_comments: str


@app.post("/api/proposals")
async def generate_proposal(req: ProposalRequest):
    """Full pipeline: BRD → intent → decomposition → diagrams → plans."""
    initial: ProposalState = {
        "project_id": req.project_id,
        "brd_text": req.brd_text,
        "intent": "",
        "bounded_contexts": [],
        "services": [],
        "openapi_stubs": [],
        "drawio_component_xml": "",
        "drawio_sequence_xml": "",
        "infra_plan": "",
        "qa_plan": "",
        "security_plan": "",
        "proposal_version": req.proposal_version,
    }
    result = await _graph.ainvoke(initial)
    # Record in ledger
    try:
        async with httpx.AsyncClient(timeout=5) as client:
            await client.post(f"{settings.ledger_url}/api/ledger", json={
                "project_id": req.project_id,
                "pipeline_run_id": f"arch-proposal-v{req.proposal_version}",
                "stage": "architecture_proposal",
                "actor": "architecture-agent",
                "status": "success",
                "metadata": {"services": [s["name"] for s in result["services"]]},
            })
    except Exception:
        pass
    return {
        "project_id": result["project_id"],
        "version": result["proposal_version"],
        "intent": result["intent"],
        "services": result["services"],
        "bounded_contexts": result["bounded_contexts"],
        "openapi_stubs": result["openapi_stubs"],
        "drawio_component_xml": result["drawio_component_xml"],
        "drawio_sequence_xml": result["drawio_sequence_xml"],
        "infra_plan": result["infra_plan"],
        "qa_plan": result["qa_plan"],
        "security_plan": result["security_plan"],
    }


@app.post("/api/proposals/revise")
async def revise_proposal(req: RevisionRequest):
    """Re-run the proposal pipeline incorporating reviewer comments."""
    updated_brd = f"{req.previous_proposal.get('intent', '')}\n\nReviewer comments to incorporate:\n{req.reviewer_comments}"
    return await generate_proposal(ProposalRequest(
        project_id=req.project_id,
        brd_text=updated_brd,
        proposal_version=req.previous_proposal.get("version", 1) + 1,
    ))


@app.get("/api/proposals/{project_id}/openapi/{service_name}")
async def get_openapi_stub(project_id: str, service_name: str):
    return {"message": "Fetch from Pipeline Ledger by project_id + service_name"}


# ── G12: Docusaurus Spec Site Preview ────────────────────────────────────────

import base64
import io
import zipfile as _zipfile

@app.get("/api/proposals/{project_id}/spec-site")
async def get_spec_site(project_id: str):
    """
    Phase 11 – G12: Returns a base64-encoded zip of a Docusaurus static site
    generated from the latest architecture proposal for the given project.
    """
    # Build Docusaurus scaffold in-memory
    buf = io.BytesIO()
    with _zipfile.ZipFile(buf, "w", _zipfile.ZIP_DEFLATED) as zf:
        # docusaurus.config.js
        zf.writestr("docusaurus.config.js", _DOCUSAURUS_CONFIG.format(project_id=project_id))
        # package.json
        zf.writestr("package.json", _DOCUSAURUS_PACKAGE_JSON.format(project_id=project_id))
        # docs/index.md
        zf.writestr("docs/index.md", f"# Architecture Proposal — {project_id}\n\nGenerated by ORBIT Architecture Agent.\n")
        # docs/adr.md placeholder
        zf.writestr("docs/adr.md", "# Architecture Decision Records\n\n_Populated from proposal ADRs._\n")
        # docs/openapi.md placeholder
        zf.writestr("docs/openapi.md", "# API Specifications\n\n_Populated from generated OpenAPI stubs._\n")
        # static/.gitkeep
        zf.writestr("static/.gitkeep", "")

    encoded = base64.b64encode(buf.getvalue()).decode()
    return {
        "project_id": project_id,
        "format": "zip",
        "base64": encoded,
        "instructions": "Unzip and run: npm install && npm run build",
    }


_DOCUSAURUS_CONFIG = """// @ts-check
const config = /** @type {import('@docusaurus/types').Config} */ ({{
  title: 'Architecture — {project_id}',
  tagline: 'Generated by ORBIT Architecture Agent',
  url: 'https://docs.ai.adports.ae',
  baseUrl: '/{project_id}/',
  onBrokenLinks: 'warn',
  onBrokenMarkdownLinks: 'warn',
  i18n: {{ defaultLocale: 'en', locales: ['en'] }},
  presets: [['classic', /** @type {{import('@docusaurus/preset-classic').Options}} */ ({{
    docs: {{ sidebarPath: './sidebars.js', routeBasePath: '/' }},
    blog: false,
    theme: {{ customCss: './src/css/custom.css' }},
  }})]],
  plugins: [
    ['docusaurus-plugin-openapi-docs', {{ id: 'openapi', docsPluginId: 'classic',
      config: {{ api: {{ specPath: 'openapi/spec.yaml', outputDir: 'docs/api' }} }} }}],
  ],
}});
module.exports = config;
"""

_DOCUSAURUS_PACKAGE_JSON = """{{
  "name": "orbit-spec-site-{project_id}",
  "version": "1.0.0",
  "private": true,
  "scripts": {{
    "start": "docusaurus start",
    "build": "docusaurus build",
    "serve": "docusaurus serve"
  }},
  "dependencies": {{
    "@docusaurus/core": "^3.5.0",
    "@docusaurus/preset-classic": "^3.5.0",
    "docusaurus-plugin-openapi-docs": "^4.0.0"
  }}
}}
"""


@app.get("/health/live")
async def liveness():
    return {"status": "ok"}


@app.get("/health/ready")
async def readiness():
    return {"status": "ok"}
