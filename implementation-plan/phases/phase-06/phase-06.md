# Phase 06 — Shared Project Context (Redis)

## Summary

Implement the **Shared Project Context** — a Redis-backed, team-shared AI collaboration memory scoped to each project. This transforms AI tool use from individual sessions into a team capability: when Developer A asks the orchestrator a question, Developer B immediately sees the context. When a decision is made, it is queryable forever. When a new team member joins, they inherit all prior context.

---

## Objectives

1. Design and implement the Redis context schema (sessions, turns, decisions).
2. Implement context write API (record a new turn from any user in the project team).
3. Implement context read API (list sessions, get turns, query decisions).
4. Implement decision extraction logic (identify decision turns from context thread).
5. Implement cross-project context referencing with explicit permission grants.
6. Implement context scrubbing (redact credentials, PII, secrets before Redis write).
7. Implement context archival (Redis TTL → cold storage in Azure Blob).
8. Wire context reads/writes to Pipeline Ledger events.
9. Implement context conflict resolution (two users writing simultaneously).
10. Wire context into the Portal API and UI (Phase 03 + Phase 04 stubs filled in).

---

## Prerequisites

- Phase 01 (Redis Cluster running).
- Phase 02 (OpenFGA auth model).
- Phase 03 (Portal API — context endpoints currently stubbed).
- Phase 04 (Portal UI — context thread view stub).

---

## Duration

**2 weeks**

**Squad:** Core Squad (1 senior .NET engineer + 1 full-stack)

---

## Deliverables

| # | Deliverable | Acceptance Criterion |
|---|------------|---------------------|
| D1 | Redis context schema | All keys follow spec; TTL verified in Redis |
| D2 | Context write API | Turn added; visible to all project team members |
| D3 | Context read API | List sessions; get turns in order; filter decisions |
| D4 | Decision extraction | Decisions tagged in context thread; queryable separately |
| D5 | Cross-project referencing | Project B team member can reference Project A context with explicit grant |
| D6 | Context scrubbing | Credentials/PII stripped before Redis write; scrubbing test suite |
| D7 | Context archival | Archived context accessible from cold store; Redis key cleaned up |
| D8 | Ledger integration | Every context read/write with cross-project reference = Ledger event |
| D9 | Conflict resolution | Concurrent writes produce deterministic merge (CRDT-style list append) |
| D10 | Portal UI integration | Context thread view shows real data; decisions highlighted |

---

## Redis Context Schema (Complete)

```
# Active session pointer
context:{projectId}:active_session
  TYPE: String
  VALUE: {sessionId}
  TTL: 7 days (rolling on activity)

# Session metadata
context:{projectId}:session:{sessionId}:meta
  TYPE: Hash
  FIELDS: created_at, creator_id, status (active|archived), turn_count
  TTL: 7 days

# Session turns (ordered list)
context:{projectId}:session:{sessionId}:turns
  TYPE: List (RPUSH/LRANGE)
  ELEMENT: JSON { turn_id, user_id, role, timestamp, type, content, artifact_refs, decision_id? }
  TTL: 7 days

# Decision index for a project (all sessions)
context:{projectId}:decisions
  TYPE: Sorted Set (score = Unix timestamp)
  MEMBER: JSON { decision_id, session_id, turn_id, decision_text, artifact_refs, decided_by }

# Cross-project reference grants
context:{projectId}:xref_grants
  TYPE: Set
  MEMBERS: {grantedProjectId} (projects allowed to reference this project's context)
  TTL: 30 days (must be renewed)

# Scrubbing rules cache
context:scrubbing:rules
  TYPE: Hash (rule_id → JSON rule)
  TTL: None (permanent, refreshed on admin update)
```

---

## Context Scrubbing

The scrubbing service applies before any content is written to Redis:

```csharp
public class ContextScrubber(IRedisDatabase redis)
{
    private static readonly Regex[] ScrubPatterns = [
        // Keycloak client secrets
        new Regex(@"client_secret\s*[:=]\s*[A-Za-z0-9\-_]{20,}", RegexOptions.IgnoreCase),
        // Connection strings with passwords
        new Regex(@"Password=[^;]{4,}", RegexOptions.IgnoreCase),
        // Bearer tokens
        new Regex(@"Bearer\s+[A-Za-z0-9\-_\.]{20,}", RegexOptions.IgnoreCase),
        // UAE national IDs
        new Regex(@"\b784-\d{4}-\d{7}-\d\b"),
        // Azure connection strings
        new Regex(@"DefaultEndpointsProtocol=https.*AccountKey=[^;]+"),
        // Vault tokens
        new Regex(@"hvs\.[A-Za-z0-9]{24,}"),
        // Private key material
        new Regex(@"-----BEGIN (RSA |EC |PRIVATE )?PRIVATE KEY-----"),
    ];

    public string Scrub(string content)
    {
        foreach (var pattern in ScrubPatterns)
            content = pattern.Replace(content, "[REDACTED]");
        return content;
    }
}
```

Scrubbing is **mandatory** — the context write endpoint will not proceed if the scrubber throws.

Additional rules from `context:scrubbing:rules` are loaded at startup and can be extended by the security team via the Portal admin UI without a deployment.

---

## Cross-Project Context Referencing

When a developer in Project A wants to reference context from Project B:

```
Developer: "@adports-orchestrator reuse the MPay retry pattern from project jul-dgd"

Orchestrator:
1. Extracts reference: project=jul-dgd, intent=MPay retry pattern
2. Checks OpenFGA: does current_user have can_read on project:jul-dgd? NO
3. Checks cross-project grants: does project:active-project have xref_grant from project:jul-dgd? NO
4. Returns: "Cross-project reference requires explicit permission. Request access to jul-dgd context."

[Tech lead of jul-dgd grants access via Portal UI]

5. Orchestrator retries: grant exists now
6. Searches jul-dgd decisions for "MPay retry" → finds decision_id XYZ
7. Returns the decision with attribution: "[From project jul-dgd, decided on 2025-11-15 by @senior-architect: Use exponential backoff with max 5 retries and DLQ]"
8. Records Pipeline Ledger event: cross-project reference from project A to project B, decision XYZ
```

---

## Context Archival Flow

```
1. Background worker runs every hour
2. Finds sessions where last_activity > 7 days
3. Serializes full session (metadata + all turns) to JSON
4. Uploads to Azure Blob: context/{projectId}/{sessionId}/{timestamp}.json.gz
5. Records blob URI in Postgres (context_archives table)
6. DEL Redis keys for the archived session
7. Records Ledger event: context.session.archived

Recovery:
GET /api/projects/{id}/context/sessions/{sessionId}/archived
→ Downloads from Blob, deserializes, returns as normal session response
```

---

## Step-by-Step Execution Plan

### Week 1

**Day 1–2:**
- [ ] Implement `IContextService` interface + Redis implementation.
- [ ] Implement `AddContextTurnCommand` with scrubbing.
- [ ] Implement `GetActiveSessionQuery` and `GetSessionTurnsQuery`.
- [ ] Unit test: turn added is readable by other team member (simulated).
- [ ] Unit test: scrubber strips all 7 patterns.

**Day 3–4:**
- [ ] Implement decision extraction logic (decisions have `type: decision` in turn JSON).
- [ ] Implement `ListProjectDecisionsQuery` (reads from Sorted Set).
- [ ] Implement cross-project grant management API.
- [ ] Implement cross-project context fetch (with Ledger recording).

**Day 5:**
- [ ] Implement context archival background worker.
- [ ] Implement archived session recovery endpoint.
- [ ] Implement conflict resolution (RPUSH is atomic — Redis guarantees ordering).

### Week 2

**Day 6–7:**
- [ ] Wire context write/read into all Ledger-relevant operations.
- [ ] Implement `context:scrubbing:rules` hot-reload in Portal admin.
- [ ] Write integration test: 3 concurrent users writing to same session.
- [ ] Write integration test: cross-project reference without grant → 403.
- [ ] Write integration test: cross-project reference with grant → returns attributed content.

**Day 8–9:**
- [ ] Fill in Portal UI context thread view with real data.
- [ ] Implement decisions panel (filtered view of decision-type turns).
- [ ] Add context thread to Project detail page (Phase 04 stub filled in).

**Day 10:**
- [ ] Load test: 100 concurrent writes to same session → all turns persisted correctly.
- [ ] Verify TTL behaviour (Redis key expires; archival picks up).
- [ ] Security review: verify scrubbing on all sensitive AD Ports patterns.

---

## Gate Criterion

- All 10 deliverables pass acceptance criteria.
- Scrubbing test suite: all 7 pattern types detected and redacted.
- Cross-project referencing works with grant; blocked without grant.
- 100 concurrent writes produce no lost turns.
- Archived sessions recoverable from Azure Blob.
- Ledger records every cross-project reference access.

---

*Phase 06 — Shared Project Context — AI Portal — v1.0*
