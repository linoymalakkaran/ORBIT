"""Hook Engine Guardrails — OPA-based policy enforcement layer for all AI agent actions.
Evaluates every agent action request against Rego policies before execution."""
from __future__ import annotations

import hashlib
import json
import logging
import time
from typing import Any, Optional

import httpx
import litellm
from fastapi import FastAPI, HTTPException, Request, status
from opentelemetry.instrumentation.fastapi import FastAPIInstrumentor
from pydantic import BaseModel, Field
from pydantic_settings import BaseSettings, SettingsConfigDict

logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO)


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_prefix="GUARDRAILS_", env_file=".env", extra="ignore")
    opa_url: str = "http://opa.ai-portal.svc:8181"
    ledger_url: str = "http://pipeline-ledger.ai-portal.svc:80"
    litellm_api_base: str = "http://litellm-gateway.litellm.svc:4000"
    litellm_api_key: str = "changeme"
    redaction_model: str = "gpt-4o-mini"
    budget_default_usd: float = 10.0


settings = Settings()

# ── OPA Policy Evaluator ─────────────────────────────────────────────────────

async def evaluate_policy(package: str, input_data: dict) -> dict:
    """Call OPA REST API to evaluate a policy package."""
    async with httpx.AsyncClient(timeout=5) as client:
        resp = await client.post(
            f"{settings.opa_url}/v1/data/{package.replace('.', '/')}",
            json={"input": input_data},
        )
        if resp.status_code != 200:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail=f"OPA policy evaluation failed: {resp.text}",
            )
        return resp.json().get("result", {})


# ── Sensitive Data Redaction ──────────────────────────────────────────────────

_SENSITIVE_PATTERNS = [
    r"\b[0-9]{4}[-\s]?[0-9]{4}[-\s]?[0-9]{4}[-\s]?[0-9]{4}\b",  # credit card
    r"\b[0-9]{3}-[0-9]{2}-[0-9]{4}\b",                             # SSN
    r"\bpassword\s*[:=]\s*\S+",                                     # passwords
    r"\bsecret\s*[:=]\s*\S+",                                       # secrets
    r"\btoken\s*[:=]\s*[A-Za-z0-9\-_.]+",                          # tokens
]

import re

def _redact_locally(text: str) -> tuple[str, list[str]]:
    """Fast regex-based redaction of obvious patterns."""
    redacted = []
    for pattern in _SENSITIVE_PATTERNS:
        matches = re.findall(pattern, text, re.IGNORECASE)
        if matches:
            redacted.extend(matches)
            text = re.sub(pattern, "[REDACTED]", text, flags=re.IGNORECASE)
    return text, redacted


async def redact_sensitive_data(prompt: str) -> tuple[str, list[str]]:
    """Redact sensitive data from prompts before sending to LLM."""
    text, redacted = _redact_locally(prompt)
    return text, redacted


# ── FastAPI ──────────────────────────────────────────────────────────────────

app = FastAPI(title="ORBIT Hook Engine Guardrails", version="1.0.0")
FastAPIInstrumentor.instrument_app(app)


class ActionEvaluationRequest(BaseModel):
    action_type: str                # e.g. "generate_code", "push_to_repo", "deploy"
    actor_id: str                   # Keycloak sub
    actor_roles: list[str]          # Keycloak roles
    project_id: str
    project_type: str               # e.g. "payment", "crm", "iac"
    agent_name: str
    payload: dict = Field(default_factory=dict)
    estimated_cost_usd: float = 0.0


class ActionEvaluationResult(BaseModel):
    allowed: bool
    reason: str
    policy_decisions: list[dict]
    redacted_fields: list[str] = Field(default_factory=list)
    requires_approval: bool = False
    approval_level: Optional[str] = None  # "manager" | "architect" | "security"
    selected_model_tier: str = "standard"   # "standard" | "premium" | "sovereign"


class BudgetCheckRequest(BaseModel):
    project_id: str
    agent_name: str
    estimated_cost_usd: float


class PromptRedactionRequest(BaseModel):
    prompt: str
    project_id: str
    actor_id: str


@app.post("/api/guardrails/evaluate", response_model=ActionEvaluationResult)
async def evaluate_action(req: ActionEvaluationRequest):
    """Evaluate an agent action against all active policies. Returns allow/deny decision."""
    policy_decisions = []
    redacted_fields: list[str] = []

    # 1. Role-based authorization check
    try:
        rbac_result = await evaluate_policy("orbit.rbac", {
            "action": req.action_type,
            "roles": req.actor_roles,
            "project_type": req.project_type,
            "agent": req.agent_name,
        })
        allowed_by_rbac = rbac_result.get("allow", False)
        policy_decisions.append({"policy": "rbac", "allowed": allowed_by_rbac, "reason": rbac_result.get("reason", "")})
    except HTTPException:
        # OPA unavailable — fail open for RBAC but log
        logger.warning("OPA unavailable; defaulting RBAC to allow")
        allowed_by_rbac = True
        policy_decisions.append({"policy": "rbac", "allowed": True, "reason": "OPA unavailable — fail open"})

    # 2. Forbidden operations check
    forbidden_actions = {"delete_production_db", "disable_security_scan", "bypass_approval"}
    if req.action_type in forbidden_actions:
        policy_decisions.append({"policy": "forbidden_ops", "allowed": False, "reason": f"Action '{req.action_type}' is forbidden"})
        await _record_policy_decision(req, False, "forbidden_operation", policy_decisions)
        return ActionEvaluationResult(
            allowed=False,
            reason=f"Action '{req.action_type}' is a forbidden operation.",
            policy_decisions=policy_decisions,
        )

    # 3. Budget limit check
    if req.estimated_cost_usd > settings.budget_default_usd:
        policy_decisions.append({
            "policy": "budget",
            "allowed": False,
            "reason": f"Estimated cost ${req.estimated_cost_usd:.2f} exceeds limit ${settings.budget_default_usd:.2f}",
        })
        await _record_policy_decision(req, False, "budget_exceeded", policy_decisions)
        return ActionEvaluationResult(
            allowed=False,
            reason="LLM budget limit exceeded for this project.",
            policy_decisions=policy_decisions,
        )
    policy_decisions.append({"policy": "budget", "allowed": True, "reason": "Within budget"})

    # 4. Sensitive data redaction check on payload
    if "prompt" in req.payload:
        redacted_prompt, fields = await redact_sensitive_data(str(req.payload.get("prompt", "")))
        redacted_fields = fields
        if fields:
            logger.warning("Sensitive data detected and redacted in payload for project %s", req.project_id)
        policy_decisions.append({"policy": "data_redaction", "allowed": True, "reason": f"Redacted {len(fields)} sensitive fields"})

    # 5. Mandatory approval gate
    requires_approval = False
    approval_level = None
    high_risk_actions = {"deploy_to_prod", "create_repo", "push_code_main", "run_migration"}
    if req.action_type in high_risk_actions and "architect" not in req.actor_roles:
        requires_approval = True
        approval_level = "architect"
        policy_decisions.append({"policy": "approval_gate", "allowed": True, "reason": "Action requires architect approval", "requires_approval": True})

    # 6. LLM tier selection
    sensitive_project_types = {"payment", "pci", "gdpr", "classified"}
    if req.project_type in sensitive_project_types:
        model_tier = "sovereign"
    elif req.action_type in {"generate_code", "architecture_design"}:
        model_tier = "premium"
    else:
        model_tier = "standard"
    policy_decisions.append({"policy": "model_tier", "allowed": True, "reason": f"Selected tier: {model_tier}"})

    overall_allowed = allowed_by_rbac and all(
        d.get("allowed", True) for d in policy_decisions
        if d["policy"] not in {"approval_gate", "data_redaction", "model_tier"}
    )

    await _record_policy_decision(req, overall_allowed, "all_policies_evaluated", policy_decisions)

    return ActionEvaluationResult(
        allowed=overall_allowed,
        reason="All policies evaluated." if overall_allowed else "One or more policies denied the action.",
        policy_decisions=policy_decisions,
        redacted_fields=redacted_fields,
        requires_approval=requires_approval,
        approval_level=approval_level,
        selected_model_tier=model_tier,
    )


@app.post("/api/guardrails/redact")
async def redact_prompt(req: PromptRedactionRequest):
    """Redact sensitive data from a prompt before sending to LLM."""
    redacted, fields = await redact_sensitive_data(req.prompt)
    return {"redacted_prompt": redacted, "redacted_fields": fields, "redaction_count": len(fields)}


@app.post("/api/guardrails/budget-check")
async def check_budget(req: BudgetCheckRequest):
    """Check if an LLM call is within the project's budget limit."""
    within_budget = req.estimated_cost_usd <= settings.budget_default_usd
    return {
        "allowed": within_budget,
        "estimated_cost_usd": req.estimated_cost_usd,
        "budget_limit_usd": settings.budget_default_usd,
        "remaining_usd": max(0.0, settings.budget_default_usd - req.estimated_cost_usd),
    }


async def _record_policy_decision(req: ActionEvaluationRequest, allowed: bool, outcome: str, decisions: list):
    """Record policy evaluation in the Pipeline Ledger for audit trail."""
    try:
        async with httpx.AsyncClient(timeout=3) as client:
            await client.post(f"{settings.ledger_url}/api/ledger", json={
                "project_id": req.project_id,
                "pipeline_run_id": f"policy-eval-{int(time.time())}",
                "stage": "policy_evaluation",
                "actor": req.actor_id,
                "status": "allowed" if allowed else "denied",
                "metadata": {
                    "action_type": req.action_type,
                    "agent": req.agent_name,
                    "outcome": outcome,
                    "decisions": decisions,
                },
            })
    except Exception:
        pass


@app.get("/health/live")
async def liveness():
    return {"status": "ok"}


@app.get("/health/ready")
async def readiness():
    try:
        async with httpx.AsyncClient(timeout=2) as client:
            resp = await client.get(f"{settings.opa_url}/health")
            opa_ok = resp.status_code == 200
    except Exception:
        opa_ok = False
    return {"status": "ok", "opa": "ok" if opa_ok else "degraded"}
