using AdPorts.AiPortal.Application.Common.Interfaces;
using MediatR;

// Context is backed by Redis (Phase 06). These are stub handlers returning empty results
// until the Redis context service is wired in Phase 06.

namespace AdPorts.AiPortal.Application.Context.Queries.GetContextSessions;
public record GetContextSessionsQuery(Guid ProjectId) : IRequest<IReadOnlyList<string>>;
public class GetContextSessionsHandler : IRequestHandler<GetContextSessionsQuery, IReadOnlyList<string>>
{
    public Task<IReadOnlyList<string>> Handle(GetContextSessionsQuery q, CancellationToken ct) =>
        Task.FromResult<IReadOnlyList<string>>([]);
}

namespace AdPorts.AiPortal.Application.Context.Queries.GetContextTurns;
public record GetContextTurnsQuery(Guid ProjectId, string SessionId) : IRequest<IReadOnlyList<object>>;
public class GetContextTurnsHandler : IRequestHandler<GetContextTurnsQuery, IReadOnlyList<object>>
{
    public Task<IReadOnlyList<object>> Handle(GetContextTurnsQuery q, CancellationToken ct) =>
        Task.FromResult<IReadOnlyList<object>>([]);
}

namespace AdPorts.AiPortal.Application.Context.Commands.AddContextTurn;
public record AddContextTurnCommand(Guid ProjectId, string SessionId, string Role, string Content) : IRequest;
public class AddContextTurnHandler : IRequestHandler<AddContextTurnCommand>
{
    public Task Handle(AddContextTurnCommand cmd, CancellationToken ct) => Task.CompletedTask;
}

namespace AdPorts.AiPortal.Application.Projects.Commands.ArchiveProject;
public record ArchiveProjectCommand(Guid Id) : IRequest;
public class ArchiveProjectHandler(IPortalDbContext db) : IRequestHandler<ArchiveProjectCommand>
{
    public async Task Handle(ArchiveProjectCommand cmd, CancellationToken ct)
    {
        var project = await db.Projects.IgnoreQueryFilters()
            .FirstOrDefaultAsync(p => p.Id == cmd.Id, ct)
            ?? throw new KeyNotFoundException($"Project {cmd.Id} not found");
        project.SetStatus("archived");
        await db.SaveChangesAsync(ct);
    }
}
