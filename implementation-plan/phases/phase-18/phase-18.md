# Phase 18 — Hook Engine & Guardrails

## Summary

Implement the **Hook Engine** — the policy enforcement layer that intercepts all AI agent actions before they are executed. Uses OPA (Open Policy Agent) with Rego policies to enforce role-based authorization, budget limits, sensitive data redaction, forbidden operations, and mandatory approval gates. Every agent action is evaluated against the policy engine before it touches any external system.

---

## Objectives

1. Implement the OPA Hook Engine server (Python/FastAPI, embedded in Orchestrator).
2. Implement role-based provisioning policies (who can start which agent for which project type).
3. Implement forbidden operations policy (actions that are always rejected regardless of role).
4. Implement budget limit policies (per-agent and per-project LLM cost caps).
5. Implement sensitive data redaction hook (intercepts prompts before they reach LLM gateway).
6. Implement mandatory approval gate enforcement (blocks execution without required approvals).
7. Implement tier-based LLM selection policy (Claude/GPT-4o/DeepSeek based on task sensitivity).
8. Implement policy audit trail (all policy decisions logged to Pipeline Ledger).
9. Implement policy admin UI in Portal (view + dry-run + override flow).
10. Implement `adports-ai policy` CLI commands.

---

## Prerequisites

- Phase 10 (Orchestrator — hook engine is called before each agent action).
- Phase 05 (Pipeline Ledger — policy decisions are recorded).
- Phase 02 (Core Data Layer — roles and permissions available).
- Phase 07 (Capability Fabric — skill read access for policy evaluation).

---

## Duration

**3 weeks**

**Squad:** Governance Squad (1 security engineer + 1 Python/AI engineer)

---

## Deliverables

| # | Deliverable | Acceptance Criterion |
|---|------------|---------------------|
| D1 | OPA Hook Engine server | Policy evaluated in < 20ms for any agent action |
| D2 | Role-based provisioning | Junior dev cannot start Backend Agent for a PROD service |
| D3 | Forbidden operations | `DROP DATABASE`, `rm -rf /`, `git push --force main` always rejected |
| D4 | Budget limits | Agent stops and requests approval when project exceeds $50 LLM budget |
| D5 | Sensitive data redaction | Secrets, PII, credentials stripped from prompts before LLM call |
| D6 | Approval gate enforcement | Architecture approval required before Backend Agent starts |
| D7 | LLM tier selection | Tasks with `sensitivity: HIGH` routed to Claude; economy tasks to DeepSeek |
| D8 | Policy audit trail | All ALLOW/DENY decisions in Pipeline Ledger |
| D9 | Policy admin UI | Architect can view policies, dry-run a proposed action, initiate override |
| D10 | CLI commands | `adports-ai policy check --action=...` and `adports-ai policy list` work |

---

## OPA Hook Engine Architecture

```
Agent requests action
        │
        ▼
┌───────────────────┐
│  Hook Engine API  │  POST /hooks/evaluate
│  (FastAPI, OPA)   │  Body: {action, context, caller}
└────────┬──────────┘
         │
         ▼ evaluate_policy()
┌───────────────────┐
│   OPA Rego Engine │  Evaluates:
│                   │  1. role_based_provisioning
│                   │  2. forbidden_operations
│                   │  3. budget_limits
│                   │  4. approval_gates
│                   │  5. llm_tier_selection
└────────┬──────────┘
         │
   ALLOW / DENY / REDACT
         │
         ▼
Agent proceeds or is blocked; decision logged to Ledger
```

---

## Core Rego Policies

### Role-Based Provisioning

```rego
# shared/hooks/role-based-provisioning.rego
package adports.hooks.provisioning

import future.keywords.if
import future.keywords.in

# Roles → allowed agent types
agent_permissions := {
    "platform_admin":    {"*"},
    "architect":         {"architecture", "backend", "frontend", "database", "integration", "devops", "qa"},
    "senior_developer":  {"backend", "frontend", "database", "integration", "qa"},
    "developer":         {"backend", "frontend", "qa"},
    "pm":                {"architecture"},
    "viewer":            set()
}

# Environment constraints
production_restricted_roles := {"platform_admin", "architect"}

allow if {
    # Caller role has permission for this agent type
    caller_roles := {r | r = input.caller.roles[_]}
    allowed_agents := {a | agent_permissions[r][a]; r = caller_roles[_]}
    input.action.agent_type in allowed_agents
}

allow if {
    # Wildcard permission
    caller_roles := {r | r = input.caller.roles[_]}
    some r in caller_roles
    "*" in agent_permissions[r]
}

deny[reason] if {
    # Block production deployments for non-elevated roles
    input.action.target_environment == "production"
    not input.caller.roles[_] in production_restricted_roles
    reason := "Production deployments require architect or platform_admin role"
}

deny[reason] if {
    # Block if caller is not the project owner or assigned engineer
    not project_member(input.caller.user_id, input.action.project_id)
    reason := sprintf("User %v is not a member of project %v", [input.caller.user_id, input.action.project_id])
}

project_member(user_id, project_id) if {
    data.projects[project_id].members[_].user_id == user_id
}
```

### Forbidden Operations

```rego
# shared/hooks/forbidden-operations.rego
package adports.hooks.forbidden

import future.keywords.if

# These patterns are ALWAYS denied regardless of role
forbidden_command_patterns := [
    "DROP DATABASE", "DROP TABLE", "TRUNCATE",
    "rm -rf", "del /f /s /q",
    "git push --force", "git push -f",
    "kubectl delete namespace",
    "pulumi destroy --yes",
    "> /dev/null 2>&1 &",         # Background process hiding
    "curl.*|.*bash",               # Curl-to-bash attacks
]

forbidden_operations := {
    "delete_production_database",
    "force_push_main_branch",
    "destroy_production_infrastructure",
    "modify_keycloak_admin_realm",
    "delete_pipeline_ledger_events",
    "bypass_approval_gate",
}

deny[reason] if {
    input.action.operation in forbidden_operations
    reason := sprintf("Operation '%v' is unconditionally forbidden", [input.action.operation])
}

deny[reason] if {
    some pattern in forbidden_command_patterns
    regex.match(pattern, input.action.command)
    reason := sprintf("Command matches forbidden pattern: %v", [pattern])
}
```

### Budget Limits

```rego
# shared/hooks/budget-limits.rego
package adports.hooks.budget

import future.keywords.if

# Per-project thresholds (USD)
project_budget_thresholds := {
    "default":           { "warn": 30,  "block": 50  },
    "pilot":             { "warn": 50,  "block": 100 },
    "enterprise":        { "warn": 200, "block": 500 },
}

deny[reason] if {
    threshold := project_budget_thresholds[input.project.tier]
    input.project.current_llm_cost_usd >= threshold.block
    reason := sprintf("Project LLM budget exceeded ($%.2f / $%.2f). Architect approval required to continue.",
        [input.project.current_llm_cost_usd, threshold.block])
}

warn[reason] if {
    threshold := project_budget_thresholds[input.project.tier]
    input.project.current_llm_cost_usd >= threshold.warn
    input.project.current_llm_cost_usd < threshold.block
    reason := sprintf("Project LLM budget at 60%% of limit ($%.2f / $%.2f).",
        [input.project.current_llm_cost_usd, threshold.block])
}
```

### Sensitive Data Redaction

```python
# Hook Engine — pre-LLM call scrubber
SENSITIVE_PATTERNS = [
    (r'(?i)(password|passwd|pwd)\s*[:=]\s*\S+',         '[REDACTED:PASSWORD]'),
    (r'(?i)(api[_-]?key|apikey)\s*[:=]\s*\S+',          '[REDACTED:API_KEY]'),
    (r'(?i)(secret|token)\s*[:=]\s*[A-Za-z0-9\-_+/=]+', '[REDACTED:SECRET]'),
    (r'\b\d{4}[\s-]\d{4}[\s-]\d{4}[\s-]\d{4}\b',       '[REDACTED:CARD_NUMBER]'),
    (r'\b[A-Z]{2}\d{2}[A-Z0-9]{11,27}\b',               '[REDACTED:IBAN]'),
    (r'\b[A-Z]{3}\d{6}[A-Z]\d\b',                        '[REDACTED:PASSPORT]'),
    (r'\b\d{3}-\d{2}-\d{4}\b',                           '[REDACTED:SSN]'),
]

def scrub_before_llm(text: str) -> tuple[str, list[str]]:
    """Remove sensitive data before sending to LLM. Returns (scrubbed_text, redacted_items)."""
    redacted = []
    for pattern, replacement in SENSITIVE_PATTERNS:
        matches = re.findall(pattern, text)
        if matches:
            redacted.extend(matches)
            text = re.sub(pattern, replacement, text)
    return text, redacted
```

---

## Hook Engine API

```python
# hook_engine/main.py
from fastapi import FastAPI
from opa_client import OPAClient

app = FastAPI()
opa = OPAClient(url=settings.OPA_URL)

@app.post("/hooks/evaluate")
async def evaluate_hook(request: HookEvaluationRequest) -> HookDecision:
    # 1. Scrub sensitive data from action payload
    clean_payload, redacted = scrub_before_llm(request.action.payload)

    # 2. Evaluate all policies
    result = await opa.query(
        policy="adports/hooks",
        input={
            "action": {**request.action.dict(), "payload": clean_payload},
            "caller": request.caller.dict(),
            "project": request.project.dict()
        }
    )

    # 3. Compose decision
    decision = HookDecision(
        allowed=len(result.deny) == 0,
        deny_reasons=result.deny,
        warnings=result.warn,
        llm_tier=result.llm_tier_selection,
        redacted_fields=redacted
    )

    # 4. Log to Pipeline Ledger
    await ledger.record(HookEvaluationEvent(
        action=request.action.operation,
        caller_id=request.caller.user_id,
        project_id=request.project.id,
        decision=decision.allowed,
        deny_reasons=decision.deny_reasons
    ))

    return decision
```

---

## Step-by-Step Execution Plan

### Week 1: OPA Server + Core Policies

- [ ] Set up OPA server embedded in Orchestrator pod.
- [ ] Implement `role-based-provisioning.rego`.
- [ ] Implement `forbidden-operations.rego`.
- [ ] Implement `budget-limits.rego`.
- [ ] Unit test: test all policy scenarios with `opa test`.

### Week 2: Redaction + Approval Gate + Tier Selection

- [ ] Implement sensitive data scrubber (7 regex patterns + contextual detection).
- [ ] Implement approval gate enforcement policy.
- [ ] Implement LLM tier selection policy.
- [ ] Implement Hook Engine FastAPI server.
- [ ] Integrate Hook Engine into Orchestrator node chain.

### Week 3: Admin UI + Audit + CLI

- [ ] Implement policy admin UI (policy viewer, dry-run, override flow).
- [ ] Implement policy audit trail in Pipeline Ledger.
- [ ] Implement `adports-ai policy check` and `adports-ai policy list` CLI commands.
- [ ] End-to-end test: junior dev blocked from Backend Agent on PROD; budget exceeded triggers approval flow.

---

## Gate Criterion

- Policy evaluation completes in < 20ms (p99) under load.
- Junior dev role blocked from starting Backend Agent for PROD service.
- `DROP DATABASE` command rejected by forbidden operations policy.
- Project exceeding $50 LLM budget triggers approval gate in Portal.
- Password in prompt redacted before LLM call; redaction logged in Ledger.
- All policy decisions visible in Pipeline Ledger with caller, action, and decision.

---

*Phase 18 — Hook Engine & Guardrails — AI Portal — v1.0*
