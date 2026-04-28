using AdPorts.AiPortal.Application.Common.Interfaces;
using AdPorts.AiPortal.Domain.Entities;
using FluentValidation;
using MediatR;
using Microsoft.EntityFrameworkCore;

namespace AdPorts.AiPortal.Application.Team.Queries.GetTeam;
public record GetTeamQuery(Guid ProjectId) : IRequest<IReadOnlyList<TeamDto>>;
public record TeamDto(Guid Id, Guid UserId, string Role, string? DisplayName, string? Email);
public class GetTeamHandler(IPortalDbContext db) : IRequestHandler<GetTeamQuery, IReadOnlyList<TeamDto>>
{
    public async Task<IReadOnlyList<TeamDto>> Handle(GetTeamQuery q, CancellationToken ct) =>
        await db.TeamMembers.AsNoTracking()
            .Where(t => t.ProjectId == q.ProjectId)
            .Select(t => new TeamDto(t.Id, t.UserId, t.Role, t.User!.DisplayName, t.User.Email))
            .ToListAsync(ct);
}

// ── Commands ─────────────────────────────────────────────────────────────────
namespace AdPorts.AiPortal.Application.Team.Commands.AddTeamMember;
public record AddTeamMemberCommand(Guid ProjectId, Guid UserId, string Role) : IRequest<Guid>;
public class AddTeamMemberValidator : AbstractValidator<AddTeamMemberCommand>
{
    public AddTeamMemberValidator() => RuleFor(x => x.Role).NotEmpty();
}
public class AddTeamMemberHandler(IPortalDbContext db) : IRequestHandler<AddTeamMemberCommand, Guid>
{
    public async Task<Guid> Handle(AddTeamMemberCommand cmd, CancellationToken ct)
    {
        var member = TeamMember.Add(cmd.ProjectId, cmd.UserId, cmd.Role);
        db.Add(member);
        await db.SaveChangesAsync(ct);
        return member.Id;
    }
}

namespace AdPorts.AiPortal.Application.Team.Commands.RemoveTeamMember;
public record RemoveTeamMemberCommand(Guid ProjectId, Guid UserId) : IRequest;
public class RemoveTeamMemberHandler(IPortalDbContext db) : IRequestHandler<RemoveTeamMemberCommand>
{
    public async Task Handle(RemoveTeamMemberCommand cmd, CancellationToken ct)
    {
        var member = await db.TeamMembers
            .FirstOrDefaultAsync(t => t.ProjectId == cmd.ProjectId && t.UserId == cmd.UserId, ct)
            ?? throw new KeyNotFoundException("Team member not found");
        db.Remove(member);
        await db.SaveChangesAsync(ct);
    }
}

namespace AdPorts.AiPortal.Application.Team.Commands.UpdateTeamMemberRole;
public record UpdateTeamMemberRoleCommand(Guid ProjectId, Guid UserId, string Role) : IRequest;
public class UpdateTeamMemberRoleHandler(IPortalDbContext db) : IRequestHandler<UpdateTeamMemberRoleCommand>
{
    public async Task Handle(UpdateTeamMemberRoleCommand cmd, CancellationToken ct)
    {
        var member = await db.TeamMembers
            .FirstOrDefaultAsync(t => t.ProjectId == cmd.ProjectId && t.UserId == cmd.UserId, ct)
            ?? throw new KeyNotFoundException("Team member not found");
        member.UpdateRole(cmd.Role);
        await db.SaveChangesAsync(ct);
    }
}
