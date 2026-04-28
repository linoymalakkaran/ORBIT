namespace AdPorts.AiPortal.Application.Context;

/// <summary>A single message in a project context thread.</summary>
public sealed record ContextMessage(
    Guid Id,
    string Role,   // "user" | "assistant" | "system"
    string Content,
    DateTime CreatedAt);

/// <summary>Service contract for managing project-scoped context threads.</summary>
public interface IContextService
{
    Task<IReadOnlyList<ContextMessage>> GetThreadAsync(Guid projectId, CancellationToken ct = default);
    Task<IReadOnlyList<ContextMessage>> AppendAsync(Guid projectId, string role, string content, CancellationToken ct = default);
    Task ClearThreadAsync(Guid projectId, CancellationToken ct = default);
}
