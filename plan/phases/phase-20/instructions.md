# Instructions — Phase 20: Multi-Tenant Project Isolation

> Add this file to your IDE's custom instructions when implementing or extending tenant isolation features.

---

## Context

You are working on **multi-tenant project isolation** for the AD Ports AI Portal. Each development project (tenant) must be completely isolated — their LLM context, secrets, costs, audit events, and Kubernetes workloads cannot leak to other projects. Isolation is enforced at multiple layers: OpenFGA (authorization), Vault (secrets), Kafka (event streams), AKS namespaces, and the Orchestrator context.

---

## Isolation Layers

```
Layer 1: Authorization   — OpenFGA: every resource check includes project_id
Layer 2: Data            — PostgreSQL: all tables have project_id, Row-Level Security enforced
Layer 3: Secrets         — Vault: each project has its own KV path /ai-portal/{project_id}/
Layer 4: K8s             — Namespace-per-project (ai-portal-{project_id})
Layer 5: Networking      — NetworkPolicy: no cross-namespace traffic
Layer 6: Audit           — EventStoreDB: stream per project ledger-{project_id}
Layer 7: LLM Context     — Orchestrator: task context always scoped to project
```

## OpenFGA Authorization Model

```
# AD Ports OpenFGA model
model
  schema 1.1

type user
type project
  relations
    define owner: [user]
    define architect: [user]
    define developer: [user] or owner or architect
    define reader: [user] or developer

type work_package
  relations
    define project: [project]
    define can_read: developer from project
    define can_execute: architect from project

type ledger_event
  relations
    define project: [project]
    define can_read: developer from project
    define can_append: developer from project     # Restricted to Orchestrator service account
```

## Row-Level Security Pattern (PostgreSQL)

```sql
-- REQUIRED: Every project-scoped table must have RLS
ALTER TABLE work_packages ENABLE ROW LEVEL SECURITY;

CREATE POLICY work_packages_project_isolation ON work_packages
    USING (project_id = current_setting('app.current_project_id')::uuid);

-- Application sets this at the start of every request:
-- SET LOCAL app.current_project_id = '{projectId}';
```

## Vault Secrets Path Convention

```
/secret/ai-portal/shared/          ← Platform-wide secrets (Orchestrator, Gateway)
/secret/ai-portal/{project_id}/    ← Project-specific secrets
    └── db-password
    └── llm-budget-override        ← Optional cost cap override
    └── external-api-key           ← Project's own integration keys
    └── signing-key                ← For Pipeline Ledger digital signatures
```

## Cross-Tenant Isolation Test Requirements

Every CI pipeline must run isolation tests:

```python
@pytest.mark.integration
async def test_project_isolation_llm_context():
    """Task from project A must not see task history from project B."""
    task_a = await create_task(project_id=PROJECT_A)
    task_b = await create_task(project_id=PROJECT_B)

    context_a = await orchestrator.get_task_context(task_a.id)
    assert task_b.id not in [t["id"] for t in context_a.history]

async def test_project_isolation_ledger():
    """Project B cannot read Project A's Ledger events."""
    async with auth_as(user=PROJECT_B_DEVELOPER):
        response = await client.get(f"/api/ledger/{PROJECT_A_ID}/events")
        assert response.status_code == 403
```

## Forbidden Patterns

| Pattern | Reason |
|---------|--------|
| LLM prompt that includes data from multiple projects | Cross-tenant data leakage |
| `SELECT * FROM table WHERE 1=1` (no project_id filter) | Returns all projects' data |
| Shared Vault path for different projects' secrets | Secrets must be project-scoped |
| Logging `project_id` of another project in same log entry | Log isolation violation |

---

*Instructions — Phase 20 — AD Ports AI Portal — Applies to: Platform Squad*
