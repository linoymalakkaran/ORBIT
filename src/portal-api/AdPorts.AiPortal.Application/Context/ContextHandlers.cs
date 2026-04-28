using AdPorts.AiPortal.Application.Common.Interfaces;
using MediatR;

// Phase 06: Context handlers wired to IContextService (Redis-backed)

// ── Query: get thread ─────────────────────────────────────────────────────────
namespace AdPorts.AiPortal.Application.Context.Queries.GetContextThread;
public record GetContextThreadQuery(Guid ProjectId) : IRequest<IReadOnlyList<ContextMessage>>;
public class GetContextThreadHandler(IContextService ctx)
    : IRequestHandler<GetContextThreadQuery, IReadOnlyList<ContextMessage>>
{
    public Task<IReadOnlyList<ContextMessage>> Handle(GetContextThreadQuery q, CancellationToken ct)
        => ctx.GetThreadAsync(q.ProjectId, ct);
}

// ── Command: append message ───────────────────────────────────────────────────
namespace AdPorts.AiPortal.Application.Context.Commands.AppendContext;
public record AppendContextCommand(Guid ProjectId, string Role, string Content)
    : IRequest<IReadOnlyList<ContextMessage>>;
public class AppendContextHandler(IContextService ctx)
    : IRequestHandler<AppendContextCommand, IReadOnlyList<ContextMessage>>
{
    public Task<IReadOnlyList<ContextMessage>> Handle(AppendContextCommand cmd, CancellationToken ct)
        => ctx.AppendAsync(cmd.ProjectId, cmd.Role, cmd.Content, ct);
}

// ── Command: clear thread ─────────────────────────────────────────────────────
namespace AdPorts.AiPortal.Application.Context.Commands.ClearContext;
public record ClearContextCommand(Guid ProjectId) : IRequest;
public class ClearContextHandler(IContextService ctx) : IRequestHandler<ClearContextCommand>
{
    public async Task Handle(ClearContextCommand cmd, CancellationToken ct)
        => await ctx.ClearThreadAsync(cmd.ProjectId, ct);
}

// ── Legacy stubs kept for backward compat (return empty) ─────────────────────
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
