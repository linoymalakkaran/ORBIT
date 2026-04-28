using AdPorts.AiPortal.Application.Common.Interfaces;
using AdPorts.AiPortal.Domain.Entities;
using MediatR;
using Microsoft.EntityFrameworkCore;

namespace AdPorts.AiPortal.Application.Projects.Queries.GetProjectById;

public record GetProjectByIdQuery(Guid Id) : IRequest<ProjectDetail?>;

public record ProjectDetail(Guid Id, string Slug, string DisplayName, string? Program,
    string? Description, string Status, DateTimeOffset CreatedAt,
    IReadOnlyList<TeamMemberDto> Team);

public record TeamMemberDto(Guid UserId, string Role, string? DisplayName);

public class GetProjectByIdHandler(IPortalDbContext db)
    : IRequestHandler<GetProjectByIdQuery, ProjectDetail?>
{
    public async Task<ProjectDetail?> Handle(GetProjectByIdQuery q, CancellationToken ct)
    {
        return await db.Projects
            .AsNoTracking()
            .Where(p => p.Id == q.Id)
            .Select(p => new ProjectDetail(
                p.Id, p.Slug, p.DisplayName, p.Program, p.Description, p.Status, p.CreatedAt,
                p.TeamMembers.Select(t => new TeamMemberDto(t.UserId, t.Role, t.User!.DisplayName)).ToList()))
            .FirstOrDefaultAsync(ct);
    }
}
