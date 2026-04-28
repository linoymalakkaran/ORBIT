using AdPorts.AiPortal.Application.Common.Interfaces;
using AdPorts.AiPortal.Domain.Entities;
using MediatR;
using Microsoft.EntityFrameworkCore;

namespace AdPorts.AiPortal.Application.Projects.Queries.GetProjects;

public record GetProjectsQuery(string? Program = null, string? Status = null, int Page = 1, int PageSize = 20)
    : IRequest<GetProjectsResult>;

public record GetProjectsResult(IReadOnlyList<ProjectSummary> Items, int Total, int Page, int PageSize);

public record ProjectSummary(Guid Id, string Slug, string DisplayName, string? Program,
    string Status, DateTimeOffset CreatedAt, int TeamSize);

public class GetProjectsQueryHandler(IPortalDbContext db) : IRequestHandler<GetProjectsQuery, GetProjectsResult>
{
    public async Task<GetProjectsResult> Handle(GetProjectsQuery q, CancellationToken ct)
    {
        var query = db.Projects.AsNoTracking();

        if (!string.IsNullOrWhiteSpace(q.Program))
            query = query.Where(p => p.Program == q.Program);
        if (!string.IsNullOrWhiteSpace(q.Status))
            query = query.Where(p => p.Status == q.Status);

        var total = await query.CountAsync(ct);
        var items = await query
            .OrderByDescending(p => p.CreatedAt)
            .Skip((q.Page - 1) * q.PageSize)
            .Take(q.PageSize)
            .Select(p => new ProjectSummary(
                p.Id, p.Slug, p.DisplayName, p.Program, p.Status, p.CreatedAt,
                p.TeamMembers.Count))
            .ToListAsync(ct);

        return new GetProjectsResult(items, total, q.Page, q.PageSize);
    }
}
