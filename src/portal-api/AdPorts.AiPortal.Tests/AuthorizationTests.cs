using System;
using System.Collections.Generic;
using System.Net.Http;
using System.Net.Http.Json;
using System.Threading.Tasks;
using Xunit;

namespace AdPorts.AiPortal.Tests;

/// <summary>
/// Phase 02 – G01: OpenFGA RBAC authorization tests.
/// Verifies that role → object permission tuples are correctly enforced.
/// Requires the openfga-seed.sh to have been run against the target store first.
/// Set env vars: OPENFGA_URL, OPENFGA_STORE_ID
/// </summary>
public class AuthorizationTests : IAsyncLifetime
{
    private readonly HttpClient _http;
    private readonly string _storeId;
    private readonly string _checkUrl;

    public AuthorizationTests()
    {
        var url = Environment.GetEnvironmentVariable("OPENFGA_URL")
                  ?? "http://openfga.ai-portal.svc:8080";
        _storeId = Environment.GetEnvironmentVariable("OPENFGA_STORE_ID")
                   ?? throw new InvalidOperationException("OPENFGA_STORE_ID env var required");
        _checkUrl = $"{url}/stores/{_storeId}/check";
        _http = new HttpClient { BaseAddress = new Uri(url) };
    }

    public Task InitializeAsync() => Task.CompletedTask;
    public Task DisposeAsync() { _http.Dispose(); return Task.CompletedTask; }

    // ── Helper ──────────────────────────────────────────────────────────────
    private async Task<bool> CheckAsync(string user, string relation, string obj)
    {
        var payload = new
        {
            tuple_key = new { user, relation, @object = obj }
        };
        var resp = await _http.PostAsJsonAsync(_checkUrl, payload);
        resp.EnsureSuccessStatusCode();
        var result = await resp.Content.ReadFromJsonAsync<CheckResponse>();
        return result?.Allowed ?? false;
    }

    // ── orbit-admin ──────────────────────────────────────────────────────────
    [Fact] public async Task OrbitAdmin_CanApprove_Project()
        => Assert.True(await CheckAsync("group:orbit-admin#member", "approve", "project:test"));

    [Fact] public async Task OrbitAdmin_CanApprove_Artifact()
        => Assert.True(await CheckAsync("group:orbit-admin#member", "approve", "artifact:test"));

    [Fact] public async Task OrbitAdmin_CanRead_LedgerEntry()
        => Assert.True(await CheckAsync("group:orbit-admin#member", "read", "ledger-entry:test"));

    // ── architect ───────────────────────────────────────────────────────────
    [Fact] public async Task Architect_CanApprove_Project()
        => Assert.True(await CheckAsync("group:architect#member", "approve", "project:demo"));

    [Fact] public async Task Architect_CanWrite_Project()
        => Assert.True(await CheckAsync("group:architect#member", "write", "project:demo"));

    [Fact] public async Task Architect_CanApprove_Artifact()
        => Assert.True(await CheckAsync("group:architect#member", "approve", "artifact:test"));

    // ── developer ───────────────────────────────────────────────────────────
    [Fact] public async Task Developer_CanRead_Project()
        => Assert.True(await CheckAsync("group:developer#member", "read", "project:demo"));

    [Fact] public async Task Developer_CannotApprove_Project()
        => Assert.False(await CheckAsync("group:developer#member", "approve", "project:demo"));

    [Fact] public async Task Developer_CanWrite_Artifact()
        => Assert.True(await CheckAsync("group:developer#member", "write", "artifact:test"));

    [Fact] public async Task Developer_CannotApprove_Artifact()
        => Assert.False(await CheckAsync("group:developer#member", "approve", "artifact:test"));

    [Fact] public async Task Developer_CanRead_Skill()
        => Assert.True(await CheckAsync("group:developer#member", "read", "skill:test"));

    // ── qa ──────────────────────────────────────────────────────────────────
    [Fact] public async Task QA_CanRead_Project()
        => Assert.True(await CheckAsync("group:qa#member", "read", "project:demo"));

    [Fact] public async Task QA_CannotApprove_Project()
        => Assert.False(await CheckAsync("group:qa#member", "approve", "project:demo"));

    // ── devops ──────────────────────────────────────────────────────────────
    [Fact] public async Task DevOps_CanRead_Project()
        => Assert.True(await CheckAsync("group:devops#member", "read", "project:demo"));

    [Fact] public async Task DevOps_CanWrite_Artifact()
        => Assert.True(await CheckAsync("group:devops#member", "write", "artifact:test"));

    // ── pci-certified ────────────────────────────────────────────────────────
    [Fact] public async Task PciCertified_CanRead_Project()
        => Assert.True(await CheckAsync("group:pci-certified#member", "read", "project:demo"));

    [Fact] public async Task PciCertified_CannotApprove_Project()
        => Assert.False(await CheckAsync("group:pci-certified#member", "approve", "project:demo"));

    [Fact] public async Task PciCertified_CannotWrite_Artifact()
        => Assert.False(await CheckAsync("group:pci-certified#member", "write", "artifact:test"));

    // ── cross-role isolation ─────────────────────────────────────────────────
    [Fact] public async Task UnknownRole_CannotRead_Project()
        => Assert.False(await CheckAsync("user:unknown-role#member", "read", "project:demo"));
}

// ── DTO ─────────────────────────────────────────────────────────────────────
file sealed record CheckResponse(bool Allowed);
