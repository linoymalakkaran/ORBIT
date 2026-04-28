using AdPorts.AiPortal.Application.Common.Interfaces;
using MediatR;
using Microsoft.EntityFrameworkCore;

namespace AdPorts.AiPortal.Application.Artifacts.Queries.GetArtifactById;

public record GetArtifactByIdQuery(Guid Id) : IRequest<ArtifactDetailDto?>;
public record ArtifactDetailDto(Guid Id, Guid ProjectId, string ArtifactType, string Version,
    string ContentHash, string StorageUri, string Metadata, DateTimeOffset CreatedAt,
    int StageNumber, string StageName, Guid? SupersededBy);

public class GetArtifactByIdHandler(IPortalDbContext db)
    : IRequestHandler<GetArtifactByIdQuery, ArtifactDetailDto?>
{
    public async Task<ArtifactDetailDto?> Handle(GetArtifactByIdQuery q, CancellationToken ct) =>
        await db.Artifacts.AsNoTracking()
            .Where(a => a.Id == q.Id)
            .Select(a => new ArtifactDetailDto(a.Id, a.ProjectId, a.ArtifactType, a.Version,
                a.ContentHash, a.StorageUri, a.Metadata, a.CreatedAt, a.StageNumber, a.StageName, a.SupersededBy))
            .FirstOrDefaultAsync(ct);
}
