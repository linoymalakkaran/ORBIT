-- V001__initial_schema.sql
-- Portal core schema — applied via DbUp

CREATE TABLE IF NOT EXISTS users (
    id              UUID PRIMARY KEY,
    username        VARCHAR(100) UNIQUE NOT NULL,
    email           VARCHAR(255) NOT NULL,
    display_name    VARCHAR(255),
    keycloak_groups TEXT[] DEFAULT '{}',
    last_seen_at    TIMESTAMPTZ,
    created_at      TIMESTAMPTZ DEFAULT now()
);

CREATE TABLE IF NOT EXISTS projects (
    id                UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    slug              VARCHAR(100) UNIQUE NOT NULL,
    display_name      VARCHAR(255) NOT NULL,
    program           VARCHAR(100),
    description       TEXT,
    status            VARCHAR(50) NOT NULL DEFAULT 'active',
    compliance_scope  JSONB DEFAULT '[]',
    stack_fingerprint JSONB,
    integration_map   JSONB DEFAULT '[]',
    deployment_state  JSONB DEFAULT '{}',
    created_at        TIMESTAMPTZ DEFAULT now(),
    updated_at        TIMESTAMPTZ DEFAULT now(),
    created_by        UUID REFERENCES users(id)
);

CREATE TABLE IF NOT EXISTS teams (
    id                     UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    project_id             UUID REFERENCES projects(id) ON DELETE CASCADE,
    user_id                UUID REFERENCES users(id),
    role                   VARCHAR(50) NOT NULL,
    opted_into_auto_impl   BOOLEAN DEFAULT false,
    pr_review_mode         VARCHAR(20) DEFAULT 'advisory',
    created_at             TIMESTAMPTZ DEFAULT now(),
    UNIQUE (project_id, user_id)
);

CREATE TABLE IF NOT EXISTS artifacts (
    id            UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    project_id    UUID REFERENCES projects(id),
    stage_number  INTEGER NOT NULL,
    stage_name    VARCHAR(100) NOT NULL,
    artifact_type VARCHAR(100) NOT NULL,
    version       VARCHAR(20) NOT NULL,
    storage_uri   TEXT NOT NULL,
    content_hash  VARCHAR(64) NOT NULL,
    metadata      JSONB DEFAULT '{}',
    created_at    TIMESTAMPTZ DEFAULT now(),
    created_by    UUID REFERENCES users(id),
    superseded_by UUID REFERENCES artifacts(id)
);

CREATE TABLE IF NOT EXISTS approvals (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    artifact_id     UUID REFERENCES artifacts(id),
    approver_id     UUID REFERENCES users(id),
    decision        VARCHAR(20) NOT NULL,
    comment         TEXT,
    signature       TEXT,
    artifact_hashes JSONB NOT NULL,
    created_at      TIMESTAMPTZ DEFAULT now()
);

CREATE TABLE IF NOT EXISTS ledger_entries (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    stream_id       VARCHAR(255) NOT NULL,
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
    previous_hash   VARCHAR(64),
    entry_hash      VARCHAR(64) UNIQUE,
    occurred_at     TIMESTAMPTZ NOT NULL,
    recorded_at     TIMESTAMPTZ DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_ledger_project ON ledger_entries(project_id, occurred_at);
CREATE INDEX IF NOT EXISTS idx_ledger_stage   ON ledger_entries(project_id, stage_number);
CREATE INDEX IF NOT EXISTS idx_ledger_actor   ON ledger_entries(actor_id, occurred_at);
CREATE INDEX IF NOT EXISTS idx_ledger_jira    ON ledger_entries USING GIN(jira_refs);
