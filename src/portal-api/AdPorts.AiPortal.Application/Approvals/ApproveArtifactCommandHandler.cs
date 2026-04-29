using System;
using System.Threading;
using System.Threading.Tasks;
using AdPorts.AiPortal.Infrastructure.Clients;
using Microsoft.Extensions.Logging;

namespace AdPorts.AiPortal.Application.Approvals;

/// <summary>
/// Phase 19 – G18: Handles artifact approval commands.
/// When an ArchitectureProposal is approved, auto-registers the project
/// in the Project Registry via ProjectRegistryClient.
/// </summary>
public sealed class ApproveArtifactCommandHandler
{
    private readonly IProjectRegistryClient _registryClient;
    private readonly ILogger<ApproveArtifactCommandHandler> _logger;

    public ApproveArtifactCommandHandler(
        IProjectRegistryClient registryClient,
        ILogger<ApproveArtifactCommandHandler> logger)
    {
        _registryClient = registryClient;
        _logger = logger;
    }

    public async Task<ApproveArtifactResult> HandleAsync(
        ApproveArtifactCommand command,
        CancellationToken ct = default)
    {
        // 1. Set artifact status to Approved (domain logic — update via repository in real implementation)
        _logger.LogInformation(
            "Approving artifact {ArtifactId} (type={ArtifactType}) for project {ProjectId}",
            command.ArtifactId, command.ArtifactType, command.ProjectId);

        // 2. If the approved artifact is an ArchitectureProposal → auto-register project
        if (string.Equals(command.ArtifactType, "ArchitectureProposal", StringComparison.OrdinalIgnoreCase))
        {
            _logger.LogInformation(
                "ArchitectureProposal approved — registering project {ProjectId} in Project Registry",
                command.ProjectId);
            try
            {
                var registration = await _registryClient.RegisterProjectAsync(
                    new RegisterProjectRequest
                    {
                        ProjectId   = command.ProjectId,
                        ProjectName = command.ProjectName ?? command.ProjectId,
                        Domain      = command.Domain ?? "Internal",
                        TenantId    = command.TenantId ?? string.Empty,
                        OwnerId     = command.ApprovedBy,
                    },
                    ct);

                _logger.LogInformation(
                    "Project {ProjectId} registered in Project Registry (alreadyExisted={Existed})",
                    registration.ProjectId, registration.AlreadyExisted);
            }
            catch (Exception ex)
            {
                // Non-fatal: approval still succeeds even if registry is temporarily unavailable
                _logger.LogWarning(ex,
                    "Failed to auto-register project {ProjectId} in Project Registry after approval",
                    command.ProjectId);
            }
        }

        return new ApproveArtifactResult
        {
            ArtifactId = command.ArtifactId,
            Status     = "Approved",
            ApprovedAt = DateTime.UtcNow,
            ApprovedBy = command.ApprovedBy,
        };
    }
}

// ── Command / Result ──────────────────────────────────────────────────────────

public sealed class ApproveArtifactCommand
{
    public string ArtifactId   { get; init; } = string.Empty;
    public string ArtifactType { get; init; } = string.Empty;   // "ArchitectureProposal" | "CodeArtifact" | ...
    public string ProjectId    { get; init; } = string.Empty;
    public string? ProjectName { get; init; }
    public string? Domain      { get; init; }
    public string? TenantId    { get; init; }
    public string ApprovedBy   { get; init; } = string.Empty;   // Keycloak user ID
}

public sealed class ApproveArtifactResult
{
    public string   ArtifactId { get; init; } = string.Empty;
    public string   Status     { get; init; } = string.Empty;
    public DateTime ApprovedAt { get; init; }
    public string   ApprovedBy { get; init; } = string.Empty;
}
