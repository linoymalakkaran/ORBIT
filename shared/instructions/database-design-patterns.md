---
owner: platform-team
version: "1.0"
next-review: "2026-10-01"
applies-to: ["backend"]
---

# Database Design Patterns

## General Principles

- Every table must have a `UUID` primary key (not serial integers) — use `gen_random_uuid()` default
- All tables include audit fields: `created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()`, `updated_at TIMESTAMPTZ`, `created_by UUID`
- Soft-delete pattern: `deleted_at TIMESTAMPTZ` column; never hard-delete business records
- Row-Level Security (RLS) on all tables containing tenant or user data

## PostgreSQL Conventions

- Schema per bounded context: `projects`, `artifacts`, `billing`, `audit`
- Indexes: cover all foreign keys and common filter columns; use `INCLUDE` for covering indexes
- JSONB for flexible payloads; index `jsonb_path_ops` for queried paths
- Use `TIMESTAMPTZ` (not `TIMESTAMP`) — always store in UTC
- Use `DECIMAL(19,4)` for monetary values — never `FLOAT` or `DOUBLE`

## EF Core Conventions (.NET)

- Use `IEntityTypeConfiguration<T>` for all entity configurations — no `[DataAnnotation]`s on domain entities
- `HasConversion` for value objects (e.g. `Money`, `ProjectStatus`)
- Migrations: one migration per feature; never edit existing migrations
- Query splitting: `AsSplitQuery()` for `Include` with collections
- Compiled queries for hot paths: `EF.CompileAsyncQuery`

## Row-Level Security

```sql
-- Enable RLS
ALTER TABLE projects ENABLE ROW LEVEL SECURITY;
ALTER TABLE projects FORCE ROW LEVEL SECURITY;

-- Policy: users see their own tenant's rows
CREATE POLICY tenant_isolation ON projects
    USING (tenant_id = current_setting('app.current_tenant_id')::uuid);
```

Set `app.current_tenant_id` via `SET LOCAL` at the start of each transaction from application layer.

## Event Sourcing (EventStoreDB)

- Stream naming: `{aggregate-type}-{aggregate-id}` (e.g. `project-3fa85f64`)
- Optimistic concurrency: always provide `expectedRevision` on append
- Projections read from `$all` stream; filter by `EventType` prefix
- Snapshots when stream length > 500 events

## Integration Patterns

- **Outbox pattern**: write domain events to `outbox_events` table in same transaction as aggregate
- **Inbox pattern**: `inbox_messages` table deduplicates incoming messages by `message_id`
- MassTransit Saga: `saga_instances` table with `CorrelationId` UUID primary key
- All integration events versioned: `ProjectCreatedV1`, `ProjectCreatedV2` — never mutate existing event contracts

## Migration Best Practices

- Migrations must be backward-compatible (blue-green deployments)
- Add columns nullable first; backfill; then add NOT NULL constraint in a later migration
- Rename via: add new column → copy data → add alias view → drop old column in next release
- Never drop columns in the same release as the code that removes their usage
