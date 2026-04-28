# Phase 05 — Pipeline Ledger (Immutable Audit)

## Summary

Implement the **Pipeline Ledger** — the most critical governance surface in the entire AI Portal. Every action the Portal ever takes is recorded here: every proposal, approval, artifact hash, agent invocation, deployment, fleet upgrade, and maintenance action. The ledger is cryptographically chained, append-only, and permanently queryable. Nothing is ever removed.

---

## Objectives

1. Implement the Ledger Event Writer service (EventStoreDB streams + cryptographic chaining).
2. Implement the Ledger Projector service (EventStoreDB → Postgres index for fast queries).
3. Implement digital signature verification for approval events.
4. Implement the Ledger Query API (REST + gRPC).
5. Implement the Ledger Verification service (chain integrity checker).
6. Wire Ledger recording into all Portal API commands from Phase 03.
7. Implement the Pipeline Ledger MCP server (enables `@adports-ledger` in IDEs).
8. Implement the Ledger Explorer UI (advanced query surface, chain verify display).
9. Implement compliance export (export full evidence package for a project as a ZIP).
10. Write comprehensive tests for chain integrity and tamper detection.

---

## Prerequisites

- Phase 01 (EventStoreDB + Kafka running).
- Phase 02 (Postgres schema, auth).
- Phase 03 (Portal API with Ledger event calls — currently stubbed).

---

## Duration

**2 weeks**

**Squad:** Core Squad (1 senior .NET engineer + 1 full-stack, parallel with Phase 05/06)

---

## Deliverables

| # | Deliverable | Acceptance Criterion |
|---|------------|---------------------|
| D1 | Ledger Event Writer | Events written to EventStoreDB with cryptographic chain; tampered event detected |
| D2 | Ledger Projector | Postgres index updated within 5 seconds of EventStoreDB event |
| D3 | Digital signature for approvals | Signature verifiable offline with Keycloak public key |
| D4 | Ledger Query API | All query patterns return correct data; chain integrity endpoint works |
| D5 | Ledger Verification service | Tampered chain produces verification failure with tampered event ID |
| D6 | Portal API ledger integration | Every state-changing command in Phase 03 API produces a ledger event |
| D7 | Pipeline Ledger MCP server | `@adports-ledger query project:X stage:5` returns events |
| D8 | Ledger Explorer UI (enhanced) | Chain verify, compliance export, cross-project graph |
| D9 | Compliance export | ZIP contains all artifacts + events + approvals for a project |
| D10 | Tamper-detection test suite | 10 tamper scenarios; all detected |

---

## Cryptographic Chaining Design

Each ledger entry for a project forms a hash chain:

```
Entry 1:  { event_data, previous_hash: "GENESIS", entry_hash: SHA256(event_data + "GENESIS") }
Entry 2:  { event_data, previous_hash: entry_1.entry_hash, entry_hash: SHA256(event_data + entry_1.entry_hash) }
Entry N:  { event_data, previous_hash: entry_N-1.entry_hash, entry_hash: SHA256(event_data + entry_N-1.entry_hash) }
```

Hash input includes:
- `event_id` (UUID)
- `event_type`
- `project_id`
- `occurred_at` (ISO 8601)
- `event_data` (canonical JSON, sorted keys)
- `actor_id`
- `previous_hash`

```csharp
public static string ComputeEntryHash(LedgerEvent ev, string previousHash)
{
    var canonical = JsonSerializer.Serialize(new {
        event_id   = ev.EventId,
        event_type = ev.EventType,
        project_id = ev.ProjectId,
        occurred_at = ev.OccurredAt.ToString("O"),
        actor_id   = ev.ActorId,
        event_data = CanonicalizeJson(ev.EventData),
        previous_hash = previousHash
    }, CanonicalJsonOptions);

    return Convert.ToHexString(SHA256.HashData(Encoding.UTF8.GetBytes(canonical))).ToLowerInvariant();
}
```

### Approval Digital Signatures

Approval events include a signature over the artifact hashes:

```csharp
// Sign: approver signs SHA256 of all artifact hashes being approved
var approvalPayload = $"{approverId}|{timestamp:O}|{string.Join(",", artifactHashes.OrderBy(x => x))}";
var signature = signingService.Sign(approvalPayload, approverCertificate);

// Verify: on query, re-derive payload and verify signature against Keycloak public key
var isValid = verificationService.Verify(approvalPayload, signature, approverKeycloakSubject);
```

Keycloak's JWKS endpoint provides the public keys for verification. This means approval signatures are verifiable by anyone with access to the Keycloak realm's JWKS endpoint.

---

## EventStoreDB Stream Design

```
# Per-project stream (primary)
project-{projectId}
  → All events for this project, in order

# Portfolio-wide stream (all projects)
$all
  → Everything (EventStoreDB built-in)

# Category streams (EventStoreDB projections)
$ce-project          → All project events
$ce-approval         → All approval events
$ce-deployment       → All deployment events
$ce-fleet-campaign   → All fleet campaign events
```

### Event Types

```
portal.project.created
portal.project.updated
portal.project.archived
portal.stage.intent-captured
portal.stage.standards-consulted
portal.stage.proposal-generated
portal.stage.proposal-revised
portal.approval.approved
portal.approval.rejected
portal.approval.changes-requested
portal.agent.delegated
portal.agent.completed
portal.agent.failed
portal.artifact.uploaded
portal.artifact.superseded
portal.deployment.initiated
portal.deployment.succeeded
portal.deployment.rolled-back
portal.fleet-campaign.created
portal.fleet-campaign.project-added
portal.fleet-campaign.wave-started
portal.fleet-campaign.project-upgraded
portal.vulnerability.cve-detected
portal.vulnerability.remediation-opened
portal.health.service-degraded
portal.health.service-recovered
portal.hook.pre-hook-blocked
portal.hook.override-recorded
```

---

## Ledger Projector (EventStoreDB → Postgres)

The Projector is a persistent subscription worker on the `$all` EventStoreDB stream:

```csharp
public class LedgerProjectorWorker(EventStoreClient esdb, IServiceScopeFactory scopeFactory)
    : BackgroundService
{
    protected override async Task ExecuteAsync(CancellationToken ct)
    {
        var sub = await esdb.SubscribeToAllAsync(
            FromAll.After(lastProcessedPosition),
            HandleEvent,
            cancellationToken: ct
        );
    }

    private async Task HandleEvent(StreamSubscription sub, ResolvedEvent re, CancellationToken ct)
    {
        using var scope = scopeFactory.CreateScope();
        var db = scope.ServiceProvider.GetRequiredService<IPortalDbContext>();

        var entry = MapToLedgerEntry(re);
        db.LedgerEntries.Add(entry);
        await db.SaveChangesAsync(ct);
    }
}
```

The projector is idempotent — if it restarts, it resumes from its last checkpointed EventStoreDB position.

---

## Ledger MCP Server

The Ledger MCP server exposes tools that developers can invoke from Copilot/Cursor:

```json
{
  "tools": [
    {
      "name": "query_ledger",
      "description": "Query Pipeline Ledger events for a project",
      "parameters": {
        "project_id": { "type": "string" },
        "stage": { "type": "integer", "optional": true },
        "event_types": { "type": "array", "items": {"type":"string"}, "optional": true },
        "from_date": { "type": "string", "optional": true },
        "to_date": { "type": "string", "optional": true }
      }
    },
    {
      "name": "verify_chain",
      "description": "Verify cryptographic chain integrity for a project",
      "parameters": {
        "project_id": { "type": "string" }
      }
    },
    {
      "name": "get_decision_trail",
      "description": "Get the full decision trail for a specific Jira ticket or BRD reference",
      "parameters": {
        "jira_ref": { "type": "string" }
      }
    },
    {
      "name": "export_evidence_package",
      "description": "Export compliance evidence package for a project as a ZIP",
      "parameters": {
        "project_id": { "type": "string" },
        "from_date": { "type": "string" },
        "to_date": { "type": "string" }
      }
    }
  ]
}
```

---

## Compliance Export

The compliance export endpoint (`GET /api/ledger/projects/{id}/export`) returns a ZIP containing:

```
evidence-{projectId}-{date}.zip
├── README.md               ← Summary: project, date range, event count, chain status
├── events.jsonl            ← All events, one per line, in chain order
├── chain-verification.json ← Chain integrity check result, with tampered event IDs if any
├── approvals/
│   ├── stage-4-approval.json   ← Approval event + signature + artifact hashes
│   └── stage-5-approval.json
├── artifacts/
│   ├── manifest.json           ← All artifacts with hashes and storage URIs
│   └── architecture-v0.2.json  ← Artifact content (for small artifacts)
└── deployments/
    └── deployment-history.json
```

---

## Step-by-Step Execution Plan

### Week 1

**Day 1–2:**
- [ ] Implement `LedgerEventWriter` service (write to EventStoreDB + compute chain hash).
- [ ] Implement `ComputeEntryHash` with canonical JSON serialization.
- [ ] Unit test: verify hash chain continuity across 100 events.
- [ ] Unit test: tampered event produces chain break detection.

**Day 3–4:**
- [ ] Implement `LedgerProjectorWorker` (persistent subscription → Postgres).
- [ ] Implement checkpoint storage (resume from last position on restart).
- [ ] Integration test: event written to ESDB appears in Postgres within 5 seconds.

**Day 5:**
- [ ] Implement digital signature service for approval events.
- [ ] Wire `ApproveStageCommand` to use signature service.
- [ ] Unit test: signature verification with Keycloak JWKS.

### Week 2

**Day 6–7:**
- [ ] Implement all Ledger Query API endpoints.
- [ ] Implement `VerifyChainIntegrityQuery` (re-hashes entire chain for a project).
- [ ] Wire all Phase 03 commands to `ILedgerService.RecordAsync`.

**Day 8–9:**
- [ ] Implement Ledger MCP server (4 tools above).
- [ ] Implement compliance export ZIP generator.
- [ ] Enhance Ledger Explorer UI with compliance export button.
- [ ] Integration test: full project lifecycle produces correct chain.

**Day 10:**
- [ ] Run tamper-detection test suite (10 scenarios).
- [ ] Verify chain in Grafana dashboard (visualize event throughput).
- [ ] Deploy Ledger Projector as separate Kubernetes Deployment.
- [ ] Load test: 1000 events/minute sustained; projector lag < 5 seconds.

---

## Gate Criterion

- All 10 deliverables pass acceptance criteria.
- Tamper-detection test suite: all 10 scenarios pass.
- Chain verification is deterministic (same chain = same result on every run).
- Compliance export ZIP contains all expected files.
- Ledger MCP server responds to all 4 tools from Cursor/Copilot.
- Performance: 1000 events/minute without projector lag > 5 seconds.

---

## Risks Specific to This Phase

| Risk | Mitigation |
|------|-----------|
| EventStoreDB persistent subscription replay on crash | Checkpoint the last processed position every N events |
| Hash collision in canonical JSON (key ordering) | Use `JsonSerializerOptions` with sorted keys; add a test vector |
| Digital signature library compatibility | Use `System.Security.Cryptography` native — no third-party crypto |
| Projector falling behind under load | Monitor projector lag metric; add backpressure if needed |

---

*Phase 05 — Pipeline Ledger — AI Portal — v1.0*
