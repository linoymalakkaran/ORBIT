using System.Net.Http;
using System.Net.Http.Json;
using System.Threading;
using System.Threading.Tasks;

namespace AdPorts.AiPortal.Infrastructure.Clients;

/// <summary>
/// Phase 19 – G18: Typed HttpClient for the Project Registry service.
/// Auto-registers a project when an ArchitectureProposal artifact is approved.
/// </summary>
public sealed class ProjectRegistryClient : IProjectRegistryClient
{
    private readonly HttpClient _http;

    public ProjectRegistryClient(HttpClient http)
    {
        _http = http;
    }

    public async Task<RegisterProjectResponse> RegisterProjectAsync(
        RegisterProjectRequest request,
        CancellationToken ct = default)
    {
        var resp = await _http.PostAsJsonAsync("/api/registry/projects", request, ct);

        if (resp.StatusCode == System.Net.HttpStatusCode.Conflict)
        {
            // Already registered — return existing entry
            var existing = await resp.Content.ReadFromJsonAsync<RegisterProjectResponse>(ct);
            return existing ?? new RegisterProjectResponse { ProjectId = request.ProjectId, AlreadyExisted = true };
        }

        resp.EnsureSuccessStatusCode();
        return await resp.Content.ReadFromJsonAsync<RegisterProjectResponse>(ct)
               ?? throw new HttpRequestException("Project Registry returned empty response");
    }
}

// ── Contracts ────────────────────────────────────────────────────────────────

public interface IProjectRegistryClient
{
    Task<RegisterProjectResponse> RegisterProjectAsync(
        RegisterProjectRequest request,
        CancellationToken ct = default);
}

public sealed class RegisterProjectRequest
{
    public string ProjectId   { get; init; } = string.Empty;
    public string ProjectName { get; init; } = string.Empty;
    public string Domain      { get; init; } = "Internal";
    public string TenantId    { get; init; } = string.Empty;
    public string OwnerId     { get; init; } = string.Empty;
}

public sealed class RegisterProjectResponse
{
    public string ProjectId     { get; init; } = string.Empty;
    public bool   AlreadyExisted { get; init; }
    public string? RegistryUrl  { get; init; }
}
