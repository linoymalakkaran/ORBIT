# Phase 02 — Core Data Layer & Identity

## Summary

With the infrastructure running, this phase establishes the foundational data layer for the Portal itself — database schemas, OpenFGA authorization model, and the identity/permission wiring that all subsequent components depend on. By the end of Phase 02, every Portal entity (Project, User, Role, Artifact, Team) has a durable, migration-managed schema and a fine-grained authorization model.

---

## Objectives

1. Design and create the Portal's PostgreSQL schema (all core tables).
2. Implement OpenFGA authorization model for Portal permissions.
3. Wire Keycloak groups to OpenFGA tuples (so group membership drives access).
4. Set up DbUp migration runner for the Portal database.
5. Create the Vault secret paths layout for all Phase 01+ components.
6. Author the Portal's core domain entities as C# records.
7. Set up the Portal's EF Core DbContext with all mappings.
8. Implement Keycloak-backed authentication for the Portal API.
9. Stand up the Portal's minimal .NET CQRS skeleton (shell without business logic).
10. Configure OpenTelemetry for all Portal services from day one.

---

## Prerequisites

- Phase 01 complete (all infrastructure running).
- PostgreSQL cluster accessible.
- Keycloak `ai-portal` realm created with groups and roles.
- Vault with Kubernetes auth configured.
- Development environment: .NET 9 SDK, EF Core CLI, Pulumi CLI.

---

## Duration

**2 weeks**

**Squad:** Core Squad (5 engineers, overlapping with Phase 01 wind-down)

---

## Deliverables

| # | Deliverable | Acceptance Criterion |
|---|------------|---------------------|
| D1 | Portal DB schema (v1 migrations) | All tables created; `dotnet ef migrations list` shows applied |
| D2 | OpenFGA authorization model | All relationship tuples queryable; RBAC test suite passes |
| D3 | Keycloak → OpenFGA sync service | Group changes sync within 30 seconds |
| D4 | Vault secret path layout | All paths documented; rotation tested |
| D5 | .NET Portal skeleton | `dotnet build` + `dotnet test` pass |
| D6 | EF Core DbContext + all entity mappings | Schema matches migrations |
| D7 | Keycloak auth middleware wired | `GET /api/health` returns 200; `/api/projects` returns 401 without token |
| D8 | OpenTelemetry instrumentation | Traces appear in Grafana Tempo; metrics in Prometheus |
| D9 | DbUp migration runner | Runs idempotently on startup; version table maintained |

---

## Database Schema Design

### Core Tables

```sql
-- Projects: every project the Portal manages
CREATE TABLE projects (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    slug            VARCHAR(100) UNIQUE NOT NULL,
    display_name    VARCHAR(255) NOT NULL,
    program         VARCHAR(100),                 -- JUL, PCS, Mirsal, internal
    description     TEXT,
    status          VARCHAR(50) NOT NULL DEFAULT 'active',
    compliance_scope JSONB DEFAULT '[]',          -- ["NESA", "ISO-27001"]
    stack_fingerprint JSONB,                      -- Version map: dotnet, angular, etc.
    integration_map  JSONB DEFAULT '[]',          -- MPay, CRM, SINTECE, etc.
    deployment_state JSONB DEFAULT '{}',          -- Per-environment state
    created_at      TIMESTAMPTZ DEFAULT now(),
    updated_at      TIMESTAMPTZ DEFAULT now(),
    created_by      UUID REFERENCES users(id)
);

-- Users: Portal users (mirrored from Keycloak, not authoritative)
CREATE TABLE users (
    id              UUID PRIMARY KEY,             -- Matches Keycloak subject claim
    username        VARCHAR(100) UNIQUE NOT NULL,
    email           VARCHAR(255) NOT NULL,
    display_name    VARCHAR(255),
    keycloak_groups TEXT[] DEFAULT '{}',
    last_seen_at    TIMESTAMPTZ,
    created_at      TIMESTAMPTZ DEFAULT now()
);

-- Teams: project teams (membership, roles)
CREATE TABLE teams (
    id          UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    project_id  UUID REFERENCES projects(id) ON DELETE CASCADE,
    user_id     UUID REFERENCES users(id),
    role        VARCHAR(50) NOT NULL,             -- architect, tech-lead, developer, qa, sre
    opted_into_auto_impl  BOOLEAN DEFAULT false,
    pr_review_mode        VARCHAR(20) DEFAULT 'advisory',  -- advisory, blocking
    created_at  TIMESTAMPTZ DEFAULT now(),
    UNIQUE (project_id, user_id)
);

-- Artifacts: every versioned artifact the Portal produces
CREATE TABLE artifacts (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    project_id      UUID REFERENCES projects(id),
    stage_number    INTEGER NOT NULL,
    stage_name      VARCHAR(100) NOT NULL,
    artifact_type   VARCHAR(100) NOT NULL,        -- architecture-diagram, openapi-spec, helm-chart...
    version         VARCHAR(20) NOT NULL,          -- 0.1, 0.2, 1.0
    storage_uri     TEXT NOT NULL,                -- Azure Blob URI
    content_hash    VARCHAR(64) NOT NULL,          -- SHA-256 hex
    metadata        JSONB DEFAULT '{}',
    created_at      TIMESTAMPTZ DEFAULT now(),
    created_by      UUID REFERENCES users(id),
    superseded_by   UUID REFERENCES artifacts(id)
);

-- Approvals: human approvals of artifacts
CREATE TABLE approvals (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    artifact_id     UUID REFERENCES artifacts(id),
    approver_id     UUID REFERENCES users(id),
    decision        VARCHAR(20) NOT NULL,          -- approved, rejected, changes-requested
    comment         TEXT,
    signature       TEXT,                         -- Digital signature
    artifact_hashes JSONB NOT NULL,               -- Exact hashes being approved
    created_at      TIMESTAMPTZ DEFAULT now()
);

-- Ledger index: fast-query index on top of EventStoreDB
CREATE TABLE ledger_entries (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    stream_id       VARCHAR(255) NOT NULL,        -- EventStoreDB stream
    event_id        VARCHAR(255) UNIQUE NOT NULL,
    event_type      VARCHAR(100) NOT NULL,
    project_id      UUID REFERENCES projects(id),
    stage_number    INTEGER,
    actor_id        UUID REFERENCES users(id),
    artifact_ids    UUID[] DEFAULT '{}',
    jira_refs       TEXT[] DEFAULT '{}',
    risk_tier       VARCHAR(20),
    compliance_tags TEXT[] DEFAULT '{}',
    event_data      JSONB NOT NULL,
    previous_hash   VARCHAR(64),                  -- Cryptographic chain
    entry_hash      VARCHAR(64) UNIQUE,
    occurred_at     TIMESTAMPTZ NOT NULL,
    recorded_at     TIMESTAMPTZ DEFAULT now()
);
CREATE INDEX idx_ledger_project ON ledger_entries(project_id, occurred_at);
CREATE INDEX idx_ledger_stage ON ledger_entries(project_id, stage_number);
CREATE INDEX idx_ledger_actor ON ledger_entries(actor_id, occurred_at);
CREATE INDEX idx_ledger_jira ON ledger_entries USING GIN(jira_refs);
```

---

## OpenFGA Authorization Model

```yaml
# Authorization model — Portal permissions
model:
  schema: 1.1

type user

type project
  relations:
    define owner: [user]
    define architect: [user] or owner
    define tech_lead: [user] or architect
    define developer: [user] or tech_lead
    define observer: [user] or developer
    define can_approve: architect or tech_lead
    define can_write: developer
    define can_read: observer
    define can_manage_fleet: [user]  # platform-engineer group
    define can_administer: [user]   # portal:admin role

type skill
  relations:
    define author: [user]
    define can_edit: author
    define can_read: [user]

type fleet_campaign
  relations:
    define manager: [user]
    define affected_tech_lead: [user]
    define can_approve: manager
    define can_view: affected_tech_lead or manager
```

### Keycloak Group → OpenFGA Tuple Sync

When a user joins the `architects` Keycloak group, a tuple is written:
```
user:alice | architect | project:*  (scoped during project onboarding)
```

A lightweight sync service polls Keycloak's admin events endpoint (or listens on the Kafka `keycloak.events` topic if the Keycloak-to-Kafka event listener is configured) and writes/deletes OpenFGA tuples accordingly.

---

## .NET Project Structure (Portal Backend Skeleton)

```
src/
├── AdPorts.AiPortal.Api/
│   ├── Program.cs
│   ├── appsettings.json
│   ├── Controllers/
│   │   └── HealthController.cs
│   └── Middleware/
│       ├── KeycloakAuthMiddleware.cs
│       └── TelemetryMiddleware.cs
├── AdPorts.AiPortal.Application/
│   ├── Common/
│   │   ├── Interfaces/
│   │   └── Behaviours/
│   │       ├── ValidationBehaviour.cs
│   │       └── LoggingBehaviour.cs
│   └── Projects/
│       └── Queries/
│           └── GetProjects/
├── AdPorts.AiPortal.Domain/
│   ├── Entities/
│   │   ├── Project.cs
│   │   ├── User.cs
│   │   ├── Artifact.cs
│   │   └── Approval.cs
│   ├── Events/
│   └── ValueObjects/
├── AdPorts.AiPortal.Infrastructure/
│   ├── Persistence/
│   │   ├── PortalDbContext.cs
│   │   ├── Migrations/
│   │   └── Configurations/
│   ├── Identity/
│   │   ├── KeycloakAuthService.cs
│   │   └── OpenFgaAuthorizationService.cs
│   ├── Messaging/
│   │   └── KafkaEventPublisher.cs
│   └── Telemetry/
│       └── TelemetryConfiguration.cs
└── AdPorts.AiPortal.Tests/
    ├── Unit/
    └── Integration/
```

---

## Step-by-Step Execution Plan

### Week 1

**Day 1–2: Schema & Migrations**
- [ ] Create the Portal project with the structure above.
- [ ] Implement all domain entities.
- [ ] Set up EF Core DbContext with all configurations.
- [ ] Create initial EF Core migration for all tables.
- [ ] Apply migration to dev Postgres. Verify via `psql`.
- [ ] Implement DbUp as an alternative runner for production (alongside EF).

**Day 3–4: Identity & Authorization**
- [ ] Wire Keycloak JWT validation middleware (use `Microsoft.AspNetCore.Authentication.JwtBearer`).
- [ ] Extract custom claims (group membership, roles) from Keycloak token.
- [ ] Deploy OpenFGA to AKS.
- [ ] Author OpenFGA model and write initial tuples for test users.
- [ ] Implement `IAuthorizationService` wrapper over OpenFGA SDK.

**Day 5: Vault Integration**
- [ ] Document full Vault secret path layout (see skill file).
- [ ] Implement `VaultConfigurationProvider` to load secrets at startup.
- [ ] Wire Vault Agent Injector annotations to all Portal pods.

### Week 2

**Day 6–7: Observability & Health**
- [ ] Add OpenTelemetry SDK to all projects (`dotnet add package OpenTelemetry.*`).
- [ ] Configure OTEL traces → Tempo, metrics → Prometheus, logs → Loki.
- [ ] Implement structured logging with `Serilog` (JSON output for Loki).
- [ ] Implement health endpoints: `/health/live`, `/health/ready`.
- [ ] Create initial Grafana dashboard: Portal API request rate + error rate.

**Day 8–9: Keycloak → OpenFGA Sync**
- [ ] Implement lightweight sync worker (background `IHostedService`).
- [ ] Listen to Keycloak admin events for group changes.
- [ ] Write/delete OpenFGA tuples based on group changes.
- [ ] Unit test sync logic with Keycloak admin API mock.

**Day 10: Integration Testing**
- [ ] Write integration test: JWT-authenticated request to `/api/projects` succeeds.
- [ ] Write integration test: unauthenticated request returns 401.
- [ ] Write integration test: developer cannot approve an artifact (OpenFGA check).
- [ ] Write integration test: architect can approve an artifact.
- [ ] Run full test suite; confirm green.

---

## Validation & Testing

```bash
# Build
dotnet build src/AdPorts.AiPortal.sln

# Run tests
dotnet test src/AdPorts.AiPortal.sln --no-build

# Check migrations are applied
dotnet ef migrations list --project src/AdPorts.AiPortal.Infrastructure

# Test auth flow
TOKEN=$(curl -s -X POST https://auth.adports-ai.internal/realms/ai-portal/protocol/openid-connect/token \
  -d "client_id=portal-web&grant_type=password&username=testarchitect&password=test123" \
  | jq -r '.access_token')
curl -H "Authorization: Bearer $TOKEN" https://api.adports-ai.internal/api/projects
```

---

## Gate Criterion

**Phase 02 is complete when:**
- All 9 deliverables pass acceptance criteria.
- Integration test suite is green (≥15 tests).
- Auth flow works end-to-end (Keycloak → JWT → API → OpenFGA check).
- OpenFGA sync service running and tuples verifiable.
- `dotnet build` + `dotnet test` pass in CI pipeline.

---

## Risks Specific to This Phase

| Risk | Mitigation |
|------|-----------|
| OpenFGA model complexity | Start with the minimal model; add relations incrementally |
| Keycloak token validation edge cases | Use official `JwtBearer` library; test with expired/invalid tokens |
| EF Core migration state drift | Use `__EFMigrationsHistory` table; DbUp as safety net |
| Schema design lock-in | JSONB columns (`metadata`, `stack_fingerprint`) allow evolution without migration |

---

## References

- [shared/skills/dotnet-cqrs-scaffold.md](../../shared/skills/dotnet-cqrs-scaffold.md)
- [shared/instructions/coding-standards-csharp.md](../../shared/instructions/coding-standards-csharp.md)
- [shared/specs/adports-keycloak-realm.schema.json](../../shared/specs/adports-keycloak-realm.schema.json)
- https://openfga.dev/docs/
- https://learn.microsoft.com/en-us/aspnet/core/security/authentication/

---

*Phase 02 — Core Data Layer & Identity — AI Portal — v1.0*
