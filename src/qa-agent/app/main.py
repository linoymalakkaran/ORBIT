"""QA Automation Agent — generates Playwright E2E tests, k6 load tests, Pact contract tests."""
from __future__ import annotations

import logging
from typing import Annotated, TypedDict
import operator

import httpx
import litellm
from fastapi import FastAPI
from langgraph.graph import END, StateGraph
from opentelemetry.instrumentation.fastapi import FastAPIInstrumentor
from pydantic import BaseModel
from pydantic_settings import BaseSettings, SettingsConfigDict

logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO)


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_prefix="QA_", env_file=".env", extra="ignore")
    litellm_api_base: str = "http://litellm-gateway.litellm.svc:4000"
    litellm_api_key: str = "changeme"
    default_model: str = "gpt-4o"
    ledger_url: str = "http://pipeline-ledger.ai-portal.svc:80"


settings = Settings()
litellm.api_base = settings.litellm_api_base
litellm.api_key = settings.litellm_api_key


class QaGenState(TypedDict):
    project_id: str
    service_name: str
    openapi_stub: str
    acceptance_criteria: list[str]
    performance_targets: dict          # {p95_ms, rps, error_rate_pct}
    playwright_tests: Annotated[list[str], operator.add]
    k6_script: str
    pact_consumer: str
    pact_provider: str
    axe_config: str
    visual_regression_config: str


async def _llm(prompt: str, system: str = "You are a senior QA automation engineer.") -> str:
    r = await litellm.acompletion(
        model=settings.default_model,
        messages=[{"role": "system", "content": system}, {"role": "user", "content": prompt}],
        temperature=0.05,
    )
    return r.choices[0].message.content or ""


async def generate_playwright_tests(state: QaGenState) -> dict:
    criteria = "\n".join(f"- {c}" for c in state["acceptance_criteria"])
    prompt = f"""Generate Playwright E2E tests for '{state['service_name']}'.

Acceptance criteria:
{criteria}

OpenAPI spec excerpt:
{state['openapi_stub'][:1500]}

Requirements:
- Use @playwright/test with TypeScript
- Page Object Model pattern
- Test each acceptance criterion
- Include: login flow (Keycloak), CRUD operations, error states
- Base URL from env: process.env.BASE_URL || 'https://{state['service_name'].lower()}.ai.adports.ae'
- Screenshot on failure: test.screenshot()
- Parallel execution with workers: 4

Output ONLY TypeScript Playwright test code."""
    code = await _llm(prompt)
    return {"playwright_tests": [code]}


async def generate_k6_script(state: QaGenState) -> dict:
    targets = state["performance_targets"]
    p95 = targets.get("p95_ms", 500)
    rps = targets.get("rps", 100)
    error_rate = targets.get("error_rate_pct", 1)

    prompt = f"""Generate k6 load test script for '{state['service_name']}'.

Performance targets:
- P95 response time: {p95}ms
- Target RPS: {rps}
- Max error rate: {error_rate}%

OpenAPI spec excerpt:
{state['openapi_stub'][:1000]}

Requirements:
- Ramp up: 0→{rps} VU over 60s, sustain 5min, ramp down 30s
- Test all main endpoints from OpenAPI spec
- Include thresholds for P95, error rate
- Use scenarios: smoke (1 VU), load (target RPS), stress (2x target)
- Auth: Bearer token from env K6_AUTH_TOKEN
- Use k6 check() for response validation

Output ONLY JavaScript k6 script."""
    code = await _llm(prompt)
    return {"k6_script": code}


async def generate_pact_tests(state: QaGenState) -> dict:
    prompt_consumer = f"""Generate Pact consumer contract test for '{state['service_name']}' in TypeScript/Jest.

OpenAPI spec:
{state['openapi_stub'][:1000]}

Requirements:
- Use @pact-foundation/pact
- Define interactions for each main endpoint
- Include request matchers (like, term, eachLike)
- Include response matchers
- Publish to Pact Broker at https://pact-broker.ai.adports.ae

Output ONLY TypeScript code."""
    prompt_provider = f"""Generate Pact provider verification test for '{state['service_name']}' in TypeScript/Jest.

Requirements:
- Use @pact-foundation/pact
- Verify against Pact Broker at https://pact-broker.ai.adports.ae
- Set up provider states (database fixtures)
- Run on CI after service deployment

Output ONLY TypeScript code."""
    consumer, provider = await _llm(prompt_consumer), await _llm(prompt_provider)
    return {"pact_consumer": consumer, "pact_provider": provider}


async def generate_axe_and_visual(state: QaGenState) -> dict:
    svc_lower = state["service_name"].lower()
    axe_config = f"""\
// axe-accessibility.config.ts — {state['service_name']}
import AxeBuilder from '@axe-core/playwright';
import {{ test, expect }} from '@playwright/test';

test.describe('Accessibility — {state['service_name']}', () => {{
  test('main page has no critical a11y violations', async ({{ page }}) => {{
    await page.goto('https://{svc_lower}.ai.adports.ae');
    const results = await new AxeBuilder({{ page }})
      .withTags(['wcag2a', 'wcag2aa', 'wcag21aa'])
      .analyze();
    expect(results.violations.filter(v => v.impact === 'critical')).toHaveLength(0);
  }});
}});
"""
    visual_config = f"""\
// visual-regression.config.ts — {state['service_name']}
import {{ test, expect }} from '@playwright/test';

test.describe('Visual Regression — {state['service_name']}', () => {{
  test('homepage matches snapshot', async ({{ page }}) => {{
    await page.goto('https://{svc_lower}.ai.adports.ae');
    await page.waitForLoadState('networkidle');
    await expect(page).toHaveScreenshot('homepage.png', {{
      maxDiffPixelRatio: 0.02,
      threshold: 0.2
    }});
  }});
}});
"""
    return {"axe_config": axe_config, "visual_regression_config": visual_config}


def _build_graph():
    g = StateGraph(QaGenState)
    for name, fn in [
        ("generate_playwright_tests", generate_playwright_tests),
        ("generate_k6_script", generate_k6_script),
        ("generate_pact_tests", generate_pact_tests),
        ("generate_axe_and_visual", generate_axe_and_visual),
    ]:
        g.add_node(name, fn)
    g.add_edge("generate_playwright_tests", "generate_k6_script")
    g.add_edge("generate_k6_script", "generate_pact_tests")
    g.add_edge("generate_pact_tests", "generate_axe_and_visual")
    g.add_edge("generate_axe_and_visual", END)
    g.set_entry_point("generate_playwright_tests")
    return g.compile()


_graph = _build_graph()

app = FastAPI(title="ORBIT QA Automation Agent", version="1.0.0")
FastAPIInstrumentor.instrument_app(app)


class QaGenRequest(BaseModel):
    project_id: str
    service_name: str
    openapi_stub: str = ""
    acceptance_criteria: list[str] = []
    performance_targets: dict = {}


@app.post("/api/generate/qa")
async def generate_qa(req: QaGenRequest):
    """Generate Playwright E2E tests, k6 load tests, Pact contracts, a11y + visual tests."""
    initial: QaGenState = {
        "project_id": req.project_id,
        "service_name": req.service_name,
        "openapi_stub": req.openapi_stub,
        "acceptance_criteria": req.acceptance_criteria,
        "performance_targets": req.performance_targets or {"p95_ms": 500, "rps": 100, "error_rate_pct": 1},
        "playwright_tests": [],
        "k6_script": "",
        "pact_consumer": "",
        "pact_provider": "",
        "axe_config": "",
        "visual_regression_config": "",
    }
    result = await _graph.ainvoke(initial)
    try:
        async with httpx.AsyncClient(timeout=5) as client:
            await client.post(f"{settings.ledger_url}/api/ledger", json={
                "project_id": req.project_id,
                "pipeline_run_id": f"qa-gen-{req.service_name}",
                "stage": "qa_generation",
                "actor": "qa-agent",
                "status": "success",
                "metadata": {"service_name": req.service_name},
            })
    except Exception:
        pass
    return {
        "project_id": result["project_id"],
        "service_name": result["service_name"],
        "artifacts": {
            "playwright_tests": result["playwright_tests"],
            "k6_script": result["k6_script"],
            "pact_consumer": result["pact_consumer"],
            "pact_provider": result["pact_provider"],
            "axe_config": result["axe_config"],
            "visual_regression_config": result["visual_regression_config"],
        },
    }


@app.get("/health/live")
async def liveness():
    return {"status": "ok"}


@app.get("/health/ready")
async def readiness():
    return {"status": "ok"}
