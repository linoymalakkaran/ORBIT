using AdPorts.AiPortal.Application.Common.Interfaces;
using MediatR;
using Microsoft.EntityFrameworkCore;

namespace AdPorts.AiPortal.Application.Artifacts.Queries.GetArtifacts;

public record GetArtifactsQuery(Guid ProjectId, int? Stage) : IRequest<IReadOnlyList<ArtifactDto>>;

public record ArtifactDto(Guid Id, string ArtifactType, string Version, string ContentHash,
    string StorageUri, DateTimeOffset CreatedAt, int StageNumber, string StageName);

public class GetArtifactsHandler(IPortalDbContext db)
    : IRequestHandler<GetArtifactsQuery, IReadOnlyList<ArtifactDto>>
{
    public async Task<IReadOnlyList<ArtifactDto>> Handle(GetArtifactsQuery q, CancellationToken ct)
    {
        var query = db.Artifacts.AsNoTracking().Where(a => a.ProjectId == q.ProjectId);
        if (q.Stage.HasValue) query = query.Where(a => a.StageNumber == q.Stage);
        return await query
            .OrderByDescending(a => a.CreatedAt)
            .Select(a => new ArtifactDto(a.Id, a.ArtifactType, a.Version, a.ContentHash,
                a.StorageUri, a.CreatedAt, a.StageNumber, a.StageName))
            .ToListAsync(ct);
    }
}
