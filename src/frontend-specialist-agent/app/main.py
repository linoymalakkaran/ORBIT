"""Frontend Specialist Agent — generates Angular 20 NX MFE scaffolds."""
from __future__ import annotations

import json
import logging
import textwrap
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
    model_config = SettingsConfigDict(env_prefix="FE_", env_file=".env", extra="ignore")
    litellm_api_base: str = "http://litellm-gateway.litellm.svc:4000"
    litellm_api_key: str = "changeme"
    default_model: str = "gpt-4o"
    ledger_url: str = "http://pipeline-ledger.ai-portal.svc:80"


settings = Settings()
litellm.api_base = settings.litellm_api_base
litellm.api_key = settings.litellm_api_key


class FrontendGenState(TypedDict):
    project_id: str
    mfe_name: str           # e.g. "payments-mfe"
    openapi_stubs: list[str]
    user_journeys: list[str]
    pages: Annotated[list[dict], operator.add]          # {name, route, components}
    components: Annotated[list[str], operator.add]       # generated TypeScript
    routing_module: str
    i18n_en: str
    i18n_ar: str
    dockerfile: str
    nginx_conf: str
    jest_tests: Annotated[list[str], operator.add]


async def _llm(prompt: str, system: str = "You are a senior Angular 20 architect.") -> str:
    r = await litellm.acompletion(
        model=settings.default_model,
        messages=[{"role": "system", "content": system}, {"role": "user", "content": prompt}],
        temperature=0.05,
    )
    return r.choices[0].message.content or ""


async def plan_pages(state: FrontendGenState) -> dict:
    journeys = "\n".join(state["user_journeys"])
    prompt = f"""From these user journeys for an MFE called '{state['mfe_name']}', identify pages and their route paths.
User journeys:
{journeys}

Output JSON array: [{{"name": "PaymentListPage", "route": "/payments", "components": ["PaymentTableComponent", "FilterBarComponent"]}}]"""
    raw = await _llm(prompt)
    try:
        import re
        m = re.search(r"\[.*?\]", raw, re.DOTALL)
        pages = json.loads(m.group(0)) if m else []
    except Exception:
        pages = [{"name": "HomePage", "route": "/", "components": ["HomeComponent"]}]
    return {"pages": pages}


async def generate_components(state: FrontendGenState) -> dict:
    components = []
    for page in state["pages"][:4]:
        prompt = f"""Generate TypeScript/Angular 20 standalone component for '{page['name']}' in MFE '{state['mfe_name']}'.

Requirements:
- Standalone component with @Component decorator
- PrimeNG UI components (p-table, p-button, p-form, etc.)
- Tailwind CSS classes
- Keycloak auth guard (inject AuthService from @orbit/auth)
- NgRx store integration (inject Store from @ngrx/store)
- Transloco i18n (inject TranslocoService)
- OnPush change detection
- Reactive forms (FormBuilder)

Output ONLY TypeScript code. Include full @Component decorator."""
        code = await _llm(prompt)
        components.append(code)
    return {"components": components}


async def generate_routing(state: FrontendGenState) -> dict:
    routes = json.dumps([{"path": p["route"].lstrip("/"), "component": p["name"]} for p in state["pages"]], indent=2)
    prompt = f"""Generate Angular 20 app.routes.ts for MFE '{state['mfe_name']}' with these routes:
{routes}

Requirements:
- Use Angular 20 standalone routing (Routes type)
- Lazy load each page component
- Apply authGuard to all protected routes
- Include a wildcard redirect to home
- Export as const routes: Routes

Output ONLY TypeScript code."""
    code = await _llm(prompt)
    return {"routing_module": code}


async def generate_i18n(state: FrontendGenState) -> dict:
    page_names = [p["name"] for p in state["pages"]]
    prompt_en = f"""Generate English (en) Transloco i18n JSON for MFE '{state['mfe_name']}' with pages: {page_names}.
Include: navigation labels, page titles, button labels, form labels, error messages.
Output ONLY valid JSON."""
    prompt_ar = f"""Generate Arabic (ar) Transloco i18n JSON for MFE '{state['mfe_name']}' with pages: {page_names}.
Include: navigation labels, page titles, button labels, form labels, error messages in Arabic.
Output ONLY valid JSON."""
    en, ar = await _llm(prompt_en), await _llm(prompt_ar)
    return {"i18n_en": en, "i18n_ar": ar}


async def generate_dockerfile_and_nginx(state: FrontendGenState) -> dict:
    mfe = state["mfe_name"]
    dockerfile = textwrap.dedent(f"""\
        # Build stage
        FROM harbor.ai.adports.ae/orbit/node:20-slim AS build
        WORKDIR /workspace
        COPY package.json package-lock.json ./
        RUN npm ci --prefer-offline
        COPY . .
        RUN npx nx build {mfe} --configuration production

        # Runtime stage
        FROM harbor.ai.adports.ae/orbit/nginx:1.27-alpine AS runtime
        COPY --from=build /workspace/dist/apps/{mfe} /usr/share/nginx/html
        COPY nginx.conf /etc/nginx/conf.d/default.conf
        EXPOSE 80
        CMD ["nginx", "-g", "daemon off;"]
    """)
    nginx_conf = textwrap.dedent("""\
        server {
            listen 80;
            root /usr/share/nginx/html;
            index index.html;

            # Security headers
            add_header X-Frame-Options "SAMEORIGIN" always;
            add_header X-Content-Type-Options "nosniff" always;
            add_header Referrer-Policy "strict-origin-when-cross-origin" always;
            add_header Content-Security-Policy "default-src 'self'; script-src 'self' 'unsafe-inline'; style-src 'self' 'unsafe-inline'" always;

            # Gzip
            gzip on;
            gzip_types text/plain text/css application/json application/javascript text/xml application/xml;

            # SPA fallback
            location / {
                try_files $uri $uri/ /index.html;
            }

            # Health check
            location /health {
                return 200 'ok';
                add_header Content-Type text/plain;
            }
        }
    """)
    return {"dockerfile": dockerfile, "nginx_conf": nginx_conf}


async def generate_jest_tests(state: FrontendGenState) -> dict:
    if not state["pages"]:
        return {"jest_tests": []}
    page = state["pages"][0]
    prompt = f"""Generate Jest + Angular Testing Library unit tests for '{page['name']}' component.

Requirements:
- Use TestBed with provideHttpClientTesting
- Mock NgRx Store with MockStore
- Mock AuthService
- Test: component creation, render title, form submission
- Use @testing-library/angular

Output ONLY TypeScript test code."""
    code = await _llm(prompt)
    return {"jest_tests": [code]}


def _build_graph():
    g = StateGraph(FrontendGenState)
    for name, fn in [
        ("plan_pages", plan_pages),
        ("generate_components", generate_components),
        ("generate_routing", generate_routing),
        ("generate_i18n", generate_i18n),
        ("generate_dockerfile_and_nginx", generate_dockerfile_and_nginx),
        ("generate_jest_tests", generate_jest_tests),
    ]:
        g.add_node(name, fn)
    g.add_edge("plan_pages", "generate_components")
    g.add_edge("generate_components", "generate_routing")
    g.add_edge("generate_routing", "generate_i18n")
    g.add_edge("generate_i18n", "generate_dockerfile_and_nginx")
    g.add_edge("generate_dockerfile_and_nginx", "generate_jest_tests")
    g.add_edge("generate_jest_tests", END)
    g.set_entry_point("plan_pages")
    return g.compile()


_graph = _build_graph()

app = FastAPI(title="ORBIT Frontend Specialist Agent", version="1.0.0")
FastAPIInstrumentor.instrument_app(app)


class FrontendGenRequest(BaseModel):
    project_id: str
    mfe_name: str
    user_journeys: list[str]
    openapi_stubs: list[str] = []


@app.post("/api/generate/frontend")
async def generate_frontend_mfe(req: FrontendGenRequest):
    """Generate a complete Angular 20 MFE scaffold."""
    initial: FrontendGenState = {
        "project_id": req.project_id,
        "mfe_name": req.mfe_name,
        "openapi_stubs": req.openapi_stubs,
        "user_journeys": req.user_journeys,
        "pages": [],
        "components": [],
        "routing_module": "",
        "i18n_en": "",
        "i18n_ar": "",
        "dockerfile": "",
        "nginx_conf": "",
        "jest_tests": [],
    }
    result = await _graph.ainvoke(initial)
    try:
        async with httpx.AsyncClient(timeout=5) as client:
            await client.post(f"{settings.ledger_url}/api/ledger", json={
                "project_id": req.project_id,
                "pipeline_run_id": f"fe-gen-{req.mfe_name}",
                "stage": "frontend_generation",
                "actor": "frontend-specialist-agent",
                "status": "success",
                "metadata": {"mfe_name": req.mfe_name, "pages": len(result["pages"])},
            })
    except Exception:
        pass
    return {
        "project_id": result["project_id"],
        "mfe_name": result["mfe_name"],
        "artifacts": {
            "pages": result["pages"],
            "components": result["components"],
            "routing_module": result["routing_module"],
            "i18n_en": result["i18n_en"],
            "i18n_ar": result["i18n_ar"],
            "dockerfile": result["dockerfile"],
            "nginx_conf": result["nginx_conf"],
            "jest_tests": result["jest_tests"],
        },
    }


@app.get("/health/live")
async def liveness():
    return {"status": "ok"}


@app.get("/health/ready")
async def readiness():
    return {"status": "ok"}
