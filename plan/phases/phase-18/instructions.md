# Instructions — Phase 18: Hook Engine & Guardrails

> Add this file to your IDE's custom instructions when working on OPA/Rego policies or the Hook Engine server.

---

## Context

You are working on the **AD Ports Hook Engine** — the OPA (Open Policy Agent) powered pre-action enforcement layer. Every agent action is evaluated here before touching any external system. This is the security and governance boundary of the entire Portal.

The Hook Engine runs embedded in the Orchestrator as a FastAPI service. OPA evaluates all Rego policy bundles. Response time MUST be < 20ms at the 99th percentile.

---

## OPA Rego Policy Rules

1. **Fail closed** — every policy file has `default allow := false`
2. **Denial reasons are human-readable strings** — not codes
3. **All policy files have corresponding `_test.rego` files** — no untested policies
4. **Package naming**: `adports.hooks.{snake_case_name}`
5. **`import future.keywords`** — use `if`, `in`, `every` syntax

```rego
# CORRECT pattern
package adports.hooks.my_policy

import future.keywords.if
import future.keywords.in

default allow := false

allow if {
    count(deny) == 0
}

deny contains reason if {
    not has_required_role
    reason := sprintf("User %v lacks required role", [input.caller.user_id])
}

# WRONG — no default = fail open risk
# package adports.hooks.bad_policy
# allow if { input.caller.roles[_] == "admin" }  ← no default false!
```

## Hook Engine API Contract

```python
# POST /hooks/evaluate
# Request:
{
    "action": {
        "type": "backend_agent.start",     # Action type (see policy files)
        "context": { ... }                  # Action-specific context
    },
    "caller": {
        "user_id": "uuid",
        "roles": ["senior_developer"],
        "project_id": "uuid"
    },
    "project": {
        "id": "uuid",
        "tier": "pilot",
        "domain": "DGD",
        "environment": "staging"
    },
    "approvals": [                          # Active approvals for this project
        {
            "id": "uuid",
            "stage": "architecture_review",
            "approver_id": "uuid",
            "approver_roles": ["architect"],
            "timestamp": "2026-04-28T10:00:00Z",
            "signature_valid": true
        }
    ],
    "task": {
        "sensitivity": "HIGH",
        "contains_pii": false,
        "is_classified": false
    }
}

# Response:
{
    "allow": true | false,
    "deny": ["string — reason 1", "string — reason 2"],   # Empty if allow=true
    "redact": ["field.path.to.redact"],                    # Fields to remove from prompt
    "selected_llm_tier": "premium | standard | economy | sovereign",
    "compliance_note": "string",
    "evaluation_time_ms": 8.2
}
```

## Adding a New Policy

1. Create `hooks/{policy_name}.rego` following the standard pattern
2. Create `hooks/{policy_name}_test.rego` with ≥ 3 allow tests and ≥ 3 deny tests
3. Create `hooks/{policy_name}_examples/allow_example.json` and `deny_example.json`
4. Add the policy file to `infrastructure/helm/hook-engine/templates/opa-policies-configmap.yaml`
5. Run `opa test hooks/ -v` — all tests must pass
6. Run `opa check hooks/` — no syntax errors
7. Submit PR — Governance Squad reviews all policy changes

## Performance Requirements

```python
# Hook Engine must respond in < 20ms for policy evaluation
# Use OPA's in-process evaluation (not HTTP) for maximum performance

import opa_client

# CORRECT: In-process OPA evaluation (zero network hop)
async def evaluate_policy(input_data: dict) -> dict:
    start = time.monotonic()
    
    result = opa_client.query(
        query="data.adports.hooks",
        input=input_data,
    )
    
    elapsed_ms = (time.monotonic() - start) * 1000
    
    if elapsed_ms > 20:
        logger.warning("Hook Engine evaluation exceeded SLA: %.1fms", elapsed_ms)
    
    return {
        "allow": result.get("allow", False),
        "deny":  list(result.get("deny", [])),
        "redact": list(result.get("redact", [])),
        "selected_llm_tier": result.get("selected_tier", "standard"),
        "evaluation_time_ms": elapsed_ms,
    }

# WRONG: HTTP call to OPA server (adds network latency)
# result = await httpx.post("http://opa-server:8181/v1/data/adports/hooks", ...)
```

## Sensitive Data Redaction Pattern

```python
# Before sending any content to an LLM, run through the redaction engine
async def redact_sensitive_content(content: str, redact_fields: list[str]) -> str:
    """
    Apply compiled regex patterns to scrub sensitive data.
    Patterns from sensitive-data-redaction.rego.
    """
    PATTERNS = {
        r"[A-Z0-9]{20}[A-Z0-9+/]{40}":              "[REDACTED-AZURE-KEY]",
        r"(?i)password\s*[:=]\s*\S+":                "[REDACTED-PASSWORD]",
        r"(?i)api[_-]?key\s*[:=]\s*\S+":            "[REDACTED-API-KEY]",
        r"\b\d{4}[- ]?\d{4}[- ]?\d{4}[- ]?\d{4}\b": "[REDACTED-CARD-NUMBER]",
        r"(?i)secret\s*[:=]\s*\S+":                  "[REDACTED-SECRET]",
        r"eyJ[A-Za-z0-9_-]{10,}\.[A-Za-z0-9_-]{10,}\.[A-Za-z0-9_-]{10,}": "[REDACTED-JWT]",
        r"\b\d{3}-\d{2}-\d{4}\b":                   "[REDACTED-SSN]",
    }
    result = content
    for pattern, replacement in PATTERNS.items():
        result = re.sub(pattern, replacement, result)
    return result
```

## Policy Review Process

All policy changes follow this process:
1. Developer authors policy + tests
2. `adports-ai policy dry-run --input=examples/*.json` passes
3. PR created with `policy-change` label
4. Governance Squad reviews (minimum 1 security engineer)
5. Test coverage ≥ 80% confirmed by `opa test --coverage`
6. Merged to main → ArgoCD deploys policy bundle to Hook Engine

## Forbidden Patterns

| Pattern | Reason |
|---------|--------|
| `default allow := true` | Fail-open is never acceptable |
| Policy without `_test.rego` | Untested policies risk false positives AND false negatives |
| Hardcoded user IDs in Rego | Use role-based checks, never user-specific rules |
| Bypassing Hook Engine via direct agent invocation | ALL agent calls must go through orchestrator |
| Removing `sensitive-data-redaction.rego` from bundle | Redaction is mandatory before any LLM call |

---

*Instructions — Phase 18 — AD Ports AI Portal — Applies to: Governance Squad*
