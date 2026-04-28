# Instructions — Phase 05: Pipeline Ledger (EventStoreDB)

> Add this file to your IDE's custom instructions when working on the Pipeline Ledger service.

---

## Context

You are building the **AD Ports Pipeline Ledger** — an immutable, cryptographically-chained audit log that records every action the AI Portal ever takes. This is the most critical governance surface in the platform. Once written, events are never updated or deleted.

The Ledger uses **EventStoreDB** as the append-only stream store and **PostgreSQL** (via projections) for fast query access.

---

## Project Structure

```
src/
├── AdPorts.Ledger.Writer/        ← Event writer service (subscribes to Portal API events)
├── AdPorts.Ledger.Projector/     ← EventStoreDB → Postgres projection service
├── AdPorts.Ledger.Api/           ← REST + gRPC query API
├── AdPorts.Ledger.Verifier/      ← Chain integrity verification service
├── AdPorts.Ledger.Mcp/           ← MCP server exposing Ledger query tools
└── AdPorts.Ledger.Tests/
```

## Immutability Contract

The Ledger has **absolute immutability rules**:
- `EventStore` streams are **append-only** — no `$maxCount` stream metadata that would expire events.
- Postgres projection table has **no `UPDATE` or `DELETE` permissions** for the Ledger service role.
- Every event has a `entry_hash` that chains to `previous_hash` — any tampering breaks verification.

```csharp
// NEVER modify these constraints — even for "cleanup" or "test data"
// NO: await _eventStore.DeleteStreamAsync(streamName, ...);
// NO: _context.Database.ExecuteSqlRaw("DELETE FROM ledger_events WHERE ...");
// NO: _context.Database.ExecuteSqlRaw("UPDATE ledger_events SET ...");
```

## Cryptographic Chaining (Canonical Implementation)

```csharp
public static string ComputeEntryHash(LedgerEvent ev, string previousHash)
{
    // Canonical JSON — keys MUST be sorted to ensure determinism
    var canonical = JsonSerializer.Serialize(
        new
        {
            event_id    = ev.EventId.ToString("N"),      // No dashes in canonical form
            event_type  = ev.EventType,
            project_id  = ev.ProjectId.ToString("N"),
            occurred_at = ev.OccurredAt.ToString("O"),   // ISO 8601 with timezone
            actor_id    = ev.ActorId,
            event_data  = ev.EventData,                   // Already canonical JSON
            previous_hash = previousHash,
        },
        new JsonSerializerOptions
        {
            PropertyNamingPolicy = JsonNamingPolicy.SnakeCaseLower,
            WriteIndented = false,                       // Compact — no whitespace
        });

    var bytes = SHA256.HashData(Encoding.UTF8.GetBytes(canonical));
    return Convert.ToHexString(bytes).ToLowerInvariant();
}
```

## EventStoreDB Stream Conventions

| Stream | Content |
|--------|---------|
| `project-{projectId}` | All events for a specific project (SCOPED) |
| `$all` | Universal stream — used by Projector subscription |
| `category-portal` | All Portal API events (EventStoreDB category projection) |

```csharp
// Append to project stream
await _eventStore.AppendToStreamAsync(
    $"project-{projectId:N}",
    StreamState.Any,    // Idempotent — do not require specific expected version
    new[] { new EventData(
        Uuid.NewUuid(),
        eventType,
        JsonSerializer.SerializeToUtf8Bytes(eventData),
        JsonSerializer.SerializeToUtf8Bytes(new { entry_hash = hash, previous_hash = prevHash })
    )}
);
```

## Digital Signature for Approval Events

Approval events MUST be signed with the approver's Keycloak-issued X.509 certificate.

```csharp
public async Task<string> SignApprovalAsync(Guid approvalId, Guid approverId, CancellationToken ct)
{
    // Fetch approver's certificate from Keycloak JWKS
    var certificate = await _keycloakClient.GetUserCertificateAsync(approverId, ct);

    // Sign the approval payload
    var payload = $"{approvalId:N}:{approverId:N}:{DateTime.UtcNow:O}";
    using var rsa = certificate.GetRSAPrivateKey()
        ?? throw new InvalidOperationException("Approver certificate has no private key");
    var signature = rsa.SignData(
        Encoding.UTF8.GetBytes(payload),
        HashAlgorithmName.SHA256,
        RSASignaturePadding.Pkcs1);

    return Convert.ToBase64String(signature);
}
```

## Verification Service

The verification service is read-only and must never produce write operations.

```csharp
public async Task<VerificationResult> VerifyChainAsync(Guid projectId, CancellationToken ct)
{
    var events = await _context.LedgerEvents
        .Where(e => e.ProjectId == projectId)
        .OrderBy(e => e.SequenceNumber)
        .AsNoTracking()
        .ToListAsync(ct);

    string previousHash = "GENESIS";
    foreach (var ev in events)
    {
        var expectedHash = ComputeEntryHash(ev, previousHash);
        if (ev.EntryHash != expectedHash)
            return VerificationResult.Failed(ev.EventId, ev.SequenceNumber, expectedHash, ev.EntryHash);
        previousHash = ev.EntryHash;
    }

    return VerificationResult.Valid(events.Count);
}
```

## Forbidden Patterns

| Pattern | Reason |
|---------|--------|
| Modifying event data after write | Immutability contract violation |
| Skipping `CancellationToken` | Ledger writes must be cancellable for graceful shutdown |
| Using `StreamState.NoStream` | Ledger streams always exist after first event — use `StreamState.Any` |
| `$maxCount` or `$maxAge` stream metadata | Events must never expire |
| Logging full `event_data` at INFO level | May contain sensitive data — log only event_type and IDs |

---

*Instructions — Phase 05 — AD Ports AI Portal — Applies to: Core Squad*
