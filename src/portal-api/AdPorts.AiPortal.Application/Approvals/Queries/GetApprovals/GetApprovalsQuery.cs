using AdPorts.AiPortal.Application.Common.Interfaces;
using MediatR;
using Microsoft.EntityFrameworkCore;

namespace AdPorts.AiPortal.Application.Approvals.Queries.GetApprovals;

public record GetApprovalsQuery(Guid ArtifactId) : IRequest<IReadOnlyList<ApprovalDto>>;
public record ApprovalDto(Guid Id, Guid ApproverId, string Decision, string? Comment,
    DateTimeOffset CreatedAt, bool HasSignature);

public class GetApprovalsHandler(IPortalDbContext db)
    : IRequestHandler<GetApprovalsQuery, IReadOnlyList<ApprovalDto>>
{
    public async Task<IReadOnlyList<ApprovalDto>> Handle(GetApprovalsQuery q, CancellationToken ct) =>
        await db.Approvals.AsNoTracking()
            .Where(a => a.ArtifactId == q.ArtifactId)
            .Select(a => new ApprovalDto(a.Id, a.ApproverId, a.Decision, a.Comment, a.CreatedAt,
                a.Signature != null))
            .ToListAsync(ct);
}
