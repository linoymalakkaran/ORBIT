# Instructions — Phase 06: Pipeline Ledger

> Add this file to your IDE's custom instructions when working on the Pipeline Ledger service.

---

## Context

You are working on the **AD Ports Pipeline Ledger** — an append-only, cryptographically-chained audit log of every significant AI action taken on the Portal. The Ledger uses EventStoreDB as its stream store, Kafka for fan-out, and PostgreSQL as a query index. The Ledger is tamper-evident: each event carries a SHA-256 hash of the previous event + its own content.

---

## Ledger Event Schema

```csharp
// LedgerEvent — the fundamental record
public record LedgerEvent
{
    public Guid     Id             { get; init; } = Guid.NewGuid();
    public string   EventType      { get; init; } = "";     // e.g. "keycloak.realm.provisioned"
    public Guid     ProjectId      { get; init; }
    public string   ActorId        { get; init; } = "";     // Keycloak subject UUID
    public JsonNode EventData      { get; init; } = new JsonObject();
    public DateTime OccurredAt     { get; init; } = DateTime.UtcNow;

    // Cryptographic chain
    public string   PreviousHash   { get; init; } = "";     // SHA-256 of previous event
    public string   EventHash      { get; init; } = "";     // SHA-256(PreviousHash + Id + EventType + EventData)
    public string?  DigitalSig     { get; init; }           // Optional: Keycloak X.509 signature
}
```

## Hash Chain Computation

```csharp
public static string ComputeEventHash(LedgerEvent previous, LedgerEvent current)
{
    // Deterministic canonical form — field order MUST be stable
    var canonical = $"{previous.EventHash}|{current.Id}|{current.EventType}|{current.ActorId}|{current.OccurredAt:O}|{current.EventData.ToJsonString()}";
    var bytes = SHA256.HashData(Encoding.UTF8.GetBytes(canonical));
    return Convert.ToHexString(bytes).ToLowerInvariant();
}

// Genesis event (first event in a project stream)
public static string ComputeGenesisHash(LedgerEvent first)
{
    var canonical = $"GENESIS|{first.Id}|{first.EventType}|{first.ActorId}|{first.OccurredAt:O}|{first.EventData.ToJsonString()}";
    var bytes = SHA256.HashData(Encoding.UTF8.GetBytes(canonical));
    return Convert.ToHexString(bytes).ToLowerInvariant();
}
```

## EventStoreDB Stream Pattern

```csharp
// Each project gets its own stream: "ledger-{projectId}"
// Events are appended with optimistic concurrency

public async Task AppendAsync(LedgerEvent evt, long expectedVersion)
{
    var streamId = $"ledger-{evt.ProjectId}";
    var eventData = new EventData(
        Uuid.FromGuid(evt.Id),
        evt.EventType,
        JsonSerializer.SerializeToUtf8Bytes(evt),
        JsonSerializer.SerializeToUtf8Bytes(new { correlationId = evt.Id })
    );

    await _client.AppendToStreamAsync(
        streamId,
        expectedVersion == -1 ? StreamRevision.None : StreamRevision.FromInt64(expectedVersion),
        new[] { eventData }
    );
}
```

## Kafka Fan-Out

Every appended event is published to Kafka for downstream consumers:

```
Topic: ledger.events
Key: {projectId}           ← Ensures ordering per project
Partition: hash(projectId) ← All events for a project go to same partition
```

## Verification API

```
GET /api/ledger/{projectId}/verify
→ Replays all events in the stream and verifies hash chain integrity
→ Returns: { "valid": true, "eventCount": 142, "firstHash": "...", "lastHash": "..." }

GET /api/ledger/{projectId}/events?from={position}&limit=50
→ Paginated event stream (read-only)

GET /api/ledger/events/type/{eventType}?from={date}&to={date}
→ Cross-project query by event type (Postgres index)
```

## Forbidden Patterns

| Pattern | Reason |
|---------|--------|
| Updating an existing Ledger event | Ledger is append-only — mutations are not permitted |
| Skipping `PreviousHash` computation | Breaks the chain — tamper detection fails |
| Querying EventStoreDB for analytics | Use Postgres index (populated by Kafka consumer) |
| Deleting events in any environment | Even dev events are permanent — use separate test streams |

---

*Instructions — Phase 06 — AD Ports AI Portal — Applies to: Platform Squad*
