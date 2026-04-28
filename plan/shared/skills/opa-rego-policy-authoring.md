# Skill: OPA Rego Policy Authoring

## Skill ID
`opa-rego-policy-authoring`

## Version
`1.0.0`

## Used By
- Phase 18 (Hook Engine & Guardrails — all policy files)
- Governance Squad (policy review and authoring)
- PR Review Agent (validates `.rego` file changes)

## Description
Standard patterns for authoring, testing, and deploying Open Policy Agent (OPA) Rego policies in the AD Ports Hook Engine. Covers rule structure, helper functions, unit test patterns, bundle organisation, and integration with the FastAPI Hook Engine server.

---

## Skill Inputs

```json
{
  "policyName": "string",             // e.g. "data-export-controls"
  "policyDescription": "string",
  "package": "string",                // e.g. "adports.hooks.data_export"
  "inputSchema": { ... },             // JSON Schema for the input document
  "rules": [                          // Rules to implement
    {
      "name": "string",               // Rule name (e.g. "deny", "allow", "redact")
      "type": "boolean|set|object",
      "description": "string"
    }
  ]
}
```

---

## Output Artefacts

```
hooks/
├── {policy_name}.rego              ← Policy implementation
├── {policy_name}_test.rego         ← OPA unit tests
└── {policy_name}_examples/
    ├── allow_example.json          ← Input that produces ALLOW
    └── deny_example.json           ← Input that produces DENY
```

---

## Rego File Structure Pattern

```rego
# hooks/{policy_name}.rego
package adports.hooks.{policy_area}

# RULE DESCRIPTIONS:
# - allow : default false; set to true when all conditions pass
# - deny  : set of denial reasons (empty set = permitted)
# - redact: set of field paths to redact from the input before processing

import future.keywords.if
import future.keywords.in
import future.keywords.every

# ─── Input contract ──────────────────────────────────────────────────────────
# Expected input fields:
#   input.caller.user_id    string  — Portal user making the request
#   input.caller.roles      array   — Keycloak realm roles for this user
#   input.action.type       string  — The action being requested
#   input.action.context    object  — Action-specific context
#   input.project.id        string  — Target project ID
#   input.project.tier      string  — "pilot"|"enterprise"|"default"
# ──────────────────────────────────────────────────────────────────────────────

default allow := false

# Grant access when no denial reasons exist
allow if {
    count(deny) == 0
}

# ─── Denial rules ─────────────────────────────────────────────────────────────

deny contains reason if {
    not has_required_role
    reason := sprintf(
        "User %v lacks required role for action %v",
        [input.caller.user_id, input.action.type]
    )
}

deny contains reason if {
    input.action.type in forbidden_operations
    reason := sprintf(
        "Operation %v is permanently forbidden",
        [input.action.type]
    )
}

# ─── Helper rules ─────────────────────────────────────────────────────────────

has_required_role if {
    required := required_roles_for_action[input.action.type]
    some role in required
    role in input.caller.roles
}

required_roles_for_action := {
    "backend_agent.start":    {"platform_admin", "architect", "senior_developer"},
    "frontend_agent.start":   {"platform_admin", "architect", "senior_developer"},
    "infra_agent.start":      {"platform_admin", "architect"},
    "fleet_upgrade.start":    {"platform_admin"},
    "ledger.export":          {"platform_admin", "auditor"},
}

forbidden_operations := {
    "database.drop_table",
    "database.drop_database",
    "infra.destroy_cluster",
    "infra.delete_namespace",
    "git.force_push_main",
    "git.delete_protected_branch",
}
```

---

## Unit Test Pattern

```rego
# hooks/{policy_name}_test.rego
package adports.hooks.{policy_area}_test

import data.adports.hooks.{policy_area}

# ─── Test: allow ──────────────────────────────────────────────────────────────

test_allow_senior_developer_backend_agent if {
    input := {
        "caller": {
            "user_id": "user-abc123",
            "roles": ["senior_developer", "developer"]
        },
        "action": {
            "type": "backend_agent.start",
            "context": {"project_id": "dgd-001"}
        },
        "project": {"id": "dgd-001", "tier": "pilot"}
    }
    {policy_area}.allow with input as input
}

# ─── Test: deny insufficient role ─────────────────────────────────────────────

test_deny_junior_developer_infra_agent if {
    input := {
        "caller": {
            "user_id": "user-junior",
            "roles": ["developer"]
        },
        "action": {
            "type": "infra_agent.start",
            "context": {}
        },
        "project": {"id": "dgd-001", "tier": "pilot"}
    }
    not {policy_area}.allow with input as input
    count({policy_area}.deny with input as input) > 0
}

# ─── Test: deny forbidden operation ───────────────────────────────────────────

test_deny_force_push_main if {
    input := {
        "caller": {
            "user_id": "admin",
            "roles": ["platform_admin"]    # Even admin cannot do this
        },
        "action": {
            "type": "git.force_push_main",
            "context": {}
        },
        "project": {"id": "any", "tier": "enterprise"}
    }
    not {policy_area}.allow with input as input
}
```

---

## Running OPA Tests

```bash
# Run all policy tests
opa test hooks/ -v

# Evaluate a specific policy with example input
opa eval --data hooks/ \
         --input hooks/role_based_provisioning_examples/allow_example.json \
         "data.adports.hooks.role_based_provisioning.allow"

# Check code coverage
opa test hooks/ --coverage --format=json | jq '.coverage'

# Bundle policies for deployment
opa build hooks/ -o hooks-bundle.tar.gz
```

---

## Hook Engine Integration Pattern

```python
# hook_engine/evaluate.py
import opa_client
from pydantic import BaseModel


class HookInput(BaseModel):
    caller:  dict    # { user_id, roles, project_id }
    action:  dict    # { type, context }
    project: dict    # { id, tier, environment }


class HookResult(BaseModel):
    allow:   bool
    deny:    list[str]  # Denial reasons
    redact:  list[str]  # Field paths to redact


async def evaluate_hooks(action_input: HookInput) -> HookResult:
    """
    Evaluate all active AD Ports policies against an action.
    Target evaluation time: < 20ms.
    """
    result = await opa_client.evaluate_policy(
        policy_path="data.adports.hooks",
        input_data=action_input.model_dump(),
    )
    return HookResult(
        allow=result.get("allow", False),
        deny=list(result.get("deny", [])),
        redact=list(result.get("redact", [])),
    )
```

---

## Policy Deployment

All policy files are deployed as an OPA bundle to the Hook Engine via Kubernetes ConfigMap + ArgoCD:

```yaml
# infrastructure/helm/hook-engine/templates/opa-policies-configmap.yaml
apiVersion: v1
kind: ConfigMap
metadata:
  name: opa-policies
  namespace: ai-portal-governance
data:
  role-based-provisioning.rego: |-
    {{ .Files.Get "policies/role-based-provisioning.rego" | indent 4 }}
  forbidden-operations.rego: |-
    {{ .Files.Get "policies/forbidden-operations.rego" | indent 4 }}
  budget-limits.rego: |-
    {{ .Files.Get "policies/budget-limits.rego" | indent 4 }}
  sensitive-data-redaction.rego: |-
    {{ .Files.Get "policies/sensitive-data-redaction.rego" | indent 4 }}
  approval-gate-enforcement.rego: |-
    {{ .Files.Get "policies/approval-gate-enforcement.rego" | indent 4 }}
  llm-tier-selection.rego: |-
    {{ .Files.Get "policies/llm-tier-selection.rego" | indent 4 }}
```

---

## Policy Authoring Rules

| Rule | Reason |
|------|--------|
| Always use `default allow := false` | Fail-closed — deny by default |
| Denial reasons must be human-readable strings | Operators can understand why action was blocked |
| Use `deny contains reason if` (not `deny = true`) | Accumulates all reasons, not just first |
| Never use `allow = true` as only check | Policy bypass risk |
| Every policy file must have a `_test.rego` | No untested policies deployed |
| Test coverage ≥ 80% (measured by OPA) | Policies must cover edge cases |
| Use `import future.keywords` | Enables `if`, `in`, `every` syntax |
| Package name = `adports.hooks.{snake_case_name}` | Consistent with Hook Engine loader |

---

## Acceptance Criteria

| # | Criterion |
|---|-----------|
| AC1 | `opa test hooks/` passes 100% (zero failures) |
| AC2 | Code coverage ≥ 80% for each policy file |
| AC3 | Policy evaluation ≤ 20ms at 99th percentile (measured in staging) |
| AC4 | `default allow := false` present in every policy |
| AC5 | Every denial reason is a human-readable string |
| AC6 | Allow/deny examples exist for every policy |
| AC7 | Policy is deployed via ConfigMap — not baked into container image |
| AC8 | Policy changes require PR Review Agent approval + Governance Squad sign-off |

---

*OPA Rego Policy Authoring Skill — AD Ports AI Portal — v1.0.0 — Owner: Governance Squad*
