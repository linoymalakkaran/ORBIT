-- Phase 02 – G03: DbUp initial schema migration
-- Applies raw SQL structures that are not covered by EF Core migrations:
-- audit_log and raw_ledger_events tables.

-- ── Audit log ──────────────────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS audit_log (
    id              BIGSERIAL       PRIMARY KEY,
    entity_type     VARCHAR(100)    NOT NULL,
    entity_id       UUID            NOT NULL,
    action          VARCHAR(50)     NOT NULL,   -- CREATE | UPDATE | DELETE | APPROVE
    performed_by    UUID            NOT NULL,   -- Keycloak user ID
    performed_at    TIMESTAMPTZ     NOT NULL DEFAULT NOW(),
    old_value       JSONB,
    new_value       JSONB,
    correlation_id  UUID,
    ip_address      INET
);

CREATE INDEX IF NOT EXISTS ix_audit_log_entity
    ON audit_log (entity_type, entity_id);

CREATE INDEX IF NOT EXISTS ix_audit_log_performed_by
    ON audit_log (performed_by);

CREATE INDEX IF NOT EXISTS ix_audit_log_performed_at
    ON audit_log (performed_at DESC);

-- ── Raw ledger events (append-only event log mirror) ─────────────────────
CREATE TABLE IF NOT EXISTS raw_ledger_events (
    id              BIGSERIAL       PRIMARY KEY,
    stream_id       UUID            NOT NULL,
    event_type      VARCHAR(200)    NOT NULL,
    event_version   INT             NOT NULL DEFAULT 1,
    payload         JSONB           NOT NULL,
    sha256_hash     CHAR(64)        NOT NULL,   -- SHA-256 of payload for chain
    prev_hash       CHAR(64),                   -- NULL for first event in stream
    recorded_at     TIMESTAMPTZ     NOT NULL DEFAULT NOW(),
    correlation_id  UUID,
    causation_id    UUID
);

CREATE UNIQUE INDEX IF NOT EXISTS ix_raw_ledger_stream_version
    ON raw_ledger_events (stream_id, event_version);

CREATE INDEX IF NOT EXISTS ix_raw_ledger_event_type
    ON raw_ledger_events (event_type);

CREATE INDEX IF NOT EXISTS ix_raw_ledger_recorded_at
    ON raw_ledger_events (recorded_at DESC);

-- ── DbUp schema version tracking (auto-managed by DbUp) ──────────────────
-- DbUp creates its own SchemaVersions table; nothing to add here.
