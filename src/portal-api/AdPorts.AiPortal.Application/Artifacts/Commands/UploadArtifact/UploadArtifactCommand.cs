using AdPorts.AiPortal.Application.Common.Interfaces;
using AdPorts.AiPortal.Domain.Entities;
using FluentValidation;
using MediatR;
using Microsoft.EntityFrameworkCore;

namespace AdPorts.AiPortal.Application.Artifacts.Commands.UploadArtifact;

public record UploadArtifactCommand(
    Guid   ProjectId,
    int    StageNumber,
    string StageName,
    string ArtifactType,
    string Version,
    string StorageUri,
    string ContentHash,
    string? Metadata = null) : IRequest<Guid>;

public class UploadArtifactValidator : AbstractValidator<UploadArtifactCommand>
{
    public UploadArtifactValidator()
    {
        RuleFor(x => x.StorageUri).NotEmpty();
        RuleFor(x => x.ContentHash).NotEmpty().Length(64);
        RuleFor(x => x.Version).NotEmpty().MaximumLength(20);
        RuleFor(x => x.StageNumber).InclusiveBetween(1, 25);
    }
}

public class UploadArtifactHandler(IPortalDbContext db, ICurrentUser currentUser)
    : IRequestHandler<UploadArtifactCommand, Guid>
{
    public async Task<Guid> Handle(UploadArtifactCommand cmd, CancellationToken ct)
    {
        var artifact = Artifact.Create(
            cmd.ProjectId, cmd.StageNumber, cmd.StageName,
            cmd.ArtifactType, cmd.Version, cmd.StorageUri, cmd.ContentHash,
            currentUser.Id, cmd.Metadata);
        db.Add(artifact);
        await db.SaveChangesAsync(ct);
        return artifact.Id;
    }
}
