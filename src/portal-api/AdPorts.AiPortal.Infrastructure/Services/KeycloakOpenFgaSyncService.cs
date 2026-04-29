using System;
using System.Collections.Generic;
using System.Linq;
using System.Net.Http;
using System.Net.Http.Json;
using System.Text.Json;
using System.Text.Json.Serialization;
using System.Threading;
using System.Threading.Tasks;
using Microsoft.Extensions.Hosting;
using Microsoft.Extensions.Logging;

namespace AdPorts.AiPortal.Infrastructure.Services;

/// <summary>
/// Phase 02 – G02: Polls Keycloak group membership every 30s and syncs
/// changes to OpenFGA relationship tuples.
/// </summary>
public sealed class KeycloakOpenFgaSyncService : BackgroundService
{
    private readonly IHttpClientFactory _httpFactory;
    private readonly ILogger<KeycloakOpenFgaSyncService> _logger;
    private readonly KeycloakOpenFgaSyncOptions _options;

    // Last-known group → members snapshot (group name → set of user IDs)
    private Dictionary<string, HashSet<string>> _snapshot = new();

    public KeycloakOpenFgaSyncService(
        IHttpClientFactory httpFactory,
        ILogger<KeycloakOpenFgaSyncService> logger,
        KeycloakOpenFgaSyncOptions options)
    {
        _httpFactory = httpFactory;
        _logger = logger;
        _options = options;
    }

    protected override async Task ExecuteAsync(CancellationToken stoppingToken)
    {
        _logger.LogInformation("KeycloakOpenFgaSyncService started (interval={Interval}s)",
            _options.PollIntervalSeconds);

        while (!stoppingToken.IsCancellationRequested)
        {
            try
            {
                await SyncOnceAsync(stoppingToken);
            }
            catch (Exception ex) when (ex is not OperationCanceledException)
            {
                _logger.LogError(ex, "Keycloak→OpenFGA sync failed; will retry next cycle");
            }

            await Task.Delay(TimeSpan.FromSeconds(_options.PollIntervalSeconds), stoppingToken);
        }
    }

    // ── Core sync logic ──────────────────────────────────────────────────────

    private async Task SyncOnceAsync(CancellationToken ct)
    {
        var keycloak = _httpFactory.CreateClient("KeycloakAdmin");
        var openfga  = _httpFactory.CreateClient("OpenFGA");

        // 1. Fetch all groups from Keycloak
        var groups = await keycloak.GetFromJsonAsync<List<KeycloakGroup>>(
            $"/admin/realms/{_options.Realm}/groups", ct) ?? [];

        var current = new Dictionary<string, HashSet<string>>();

        foreach (var group in groups)
        {
            var members = await keycloak.GetFromJsonAsync<List<KeycloakUser>>(
                $"/admin/realms/{_options.Realm}/groups/{group.Id}/members", ct) ?? [];

            current[group.Name] = members.Select(m => m.Id).ToHashSet();
        }

        // 2. Diff against snapshot
        var writes  = new List<OpenFgaTupleKey>();
        var deletes = new List<OpenFgaTupleKey>();

        foreach (var (groupName, memberIds) in current)
        {
            _snapshot.TryGetValue(groupName, out var previousMembers);
            previousMembers ??= [];

            // New members → write tuples
            foreach (var userId in memberIds.Except(previousMembers))
            {
                foreach (var (relation, obj) in GroupToTuples(groupName))
                    writes.Add(new OpenFgaTupleKey($"user:{userId}", relation, obj));
            }

            // Removed members → delete tuples
            foreach (var userId in previousMembers.Except(memberIds))
            {
                foreach (var (relation, obj) in GroupToTuples(groupName))
                    deletes.Add(new OpenFgaTupleKey($"user:{userId}", relation, obj));
            }
        }

        if (writes.Count == 0 && deletes.Count == 0)
        {
            _logger.LogDebug("KeycloakOpenFgaSync: no changes detected");
            _snapshot = current;
            return;
        }

        // 3. Write to OpenFGA in batches of 20 (API limit)
        foreach (var batch in writes.Chunk(20))
            await WriteOpenFgaAsync(openfga, batch, [], ct);

        foreach (var batch in deletes.Chunk(20))
            await WriteOpenFgaAsync(openfga, [], batch, ct);

        _logger.LogInformation(
            "KeycloakOpenFgaSync: applied {Writes} writes, {Deletes} deletes",
            writes.Count, deletes.Count);

        // 4. Record to Pipeline Ledger
        await RecordLedgerEventAsync(writes.Count, deletes.Count, ct);

        _snapshot = current;
    }

    // ── Mapping: Keycloak group name → list of (relation, object) tuples ─────

    private static IEnumerable<(string Relation, string Object)> GroupToTuples(string groupName)
        => groupName switch
        {
            "orbit-admin" => [
                ("approve", "project:*"), ("read", "project:*"), ("write", "project:*"),
                ("approve", "artifact:*"), ("read", "artifact:*"),
                ("approve", "skill:*"),   ("read", "skill:*"),
                ("read", "ledger-entry:*")
            ],
            "architect" => [
                ("approve", "project:*"), ("read", "project:*"), ("write", "project:*"),
                ("approve", "artifact:*"), ("read", "artifact:*"),
                ("read", "skill:*"), ("read", "ledger-entry:*")
            ],
            "developer" => [
                ("read", "project:*"),
                ("write", "artifact:*"), ("read", "artifact:*"),
                ("read", "skill:*"), ("read", "ledger-entry:*")
            ],
            "qa" => [
                ("read", "project:*"),
                ("read", "artifact:*"), ("write", "artifact:*"),
                ("read", "skill:*"), ("read", "ledger-entry:*")
            ],
            "devops" => [
                ("read", "project:*"),
                ("read", "artifact:*"), ("write", "artifact:*"),
                ("read", "skill:*"), ("read", "ledger-entry:*")
            ],
            "pci-certified" => [
                ("read", "project:*"), ("read", "ledger-entry:*")
            ],
            _ => []
        };

    // ── HTTP helpers ─────────────────────────────────────────────────────────

    private async Task WriteOpenFgaAsync(
        HttpClient openfga,
        IEnumerable<OpenFgaTupleKey> writes,
        IEnumerable<OpenFgaTupleKey> deletes,
        CancellationToken ct)
    {
        var payload = new
        {
            writes  = writes.Any()  ? new { tuple_keys = writes }  : null,
            deletes = deletes.Any() ? new { tuple_keys = deletes } : null
        };

        var resp = await openfga.PostAsJsonAsync(
            $"/stores/{_options.OpenFgaStoreId}/write", payload, ct);

        if (!resp.IsSuccessStatusCode)
        {
            var body = await resp.Content.ReadAsStringAsync(ct);
            _logger.LogWarning("OpenFGA write returned {Status}: {Body}", resp.StatusCode, body);
        }
    }

    private async Task RecordLedgerEventAsync(int writes, int deletes, CancellationToken ct)
    {
        try
        {
            var ledgerClient = _httpFactory.CreateClient("PipelineLedger");
            var payload = new
            {
                event_type = "keycloak_openfga_sync",
                payload    = new { writes, deletes, timestamp = DateTime.UtcNow }
            };
            await ledgerClient.PostAsJsonAsync("/api/ledger", payload, ct);
        }
        catch (Exception ex)
        {
            _logger.LogWarning(ex, "Failed to record ledger event for sync");
        }
    }

    // ── DTOs ─────────────────────────────────────────────────────────────────

    private sealed record KeycloakGroup(
        [property: JsonPropertyName("id")]   string Id,
        [property: JsonPropertyName("name")] string Name);

    private sealed record KeycloakUser(
        [property: JsonPropertyName("id")]       string Id,
        [property: JsonPropertyName("username")] string Username);

    private sealed record OpenFgaTupleKey(
        [property: JsonPropertyName("user")]     string User,
        [property: JsonPropertyName("relation")] string Relation,
        [property: JsonPropertyName("object")]   string Object);
}

// ── Options ──────────────────────────────────────────────────────────────────

public sealed class KeycloakOpenFgaSyncOptions
{
    public string Realm              { get; init; } = "ai-portal";
    public string OpenFgaStoreId    { get; init; } = string.Empty;
    public int    PollIntervalSeconds { get; init; } = 30;
}
