using AdPorts.AiPortal.Application.Context;
using AdPorts.AiPortal.Application.Interfaces;
using StackExchange.Redis;
using System.Text.Json;

namespace AdPorts.AiPortal.Infrastructure.Services;

/// <summary>
/// Redis-backed implementation of IContextService.
/// Context threads are stored as Redis lists (RPUSH/LRANGE) keyed by projectId.
/// </summary>
public sealed class RedisContextService : IContextService
{
    private const int MaxMessages = 200;
    private readonly IConnectionMultiplexer _redis;

    public RedisContextService(IConnectionMultiplexer redis)
    {
        _redis = redis;
    }

    private static string Key(Guid projectId) => $"context:{projectId}";

    public async Task<IReadOnlyList<ContextMessage>> GetThreadAsync(
        Guid projectId, CancellationToken ct = default)
    {
        var db = _redis.GetDatabase();
        var raw = await db.ListRangeAsync(Key(projectId), 0, -1);
        return raw
            .Select(r => JsonSerializer.Deserialize<ContextMessage>(r!)!)
            .ToList()
            .AsReadOnly();
    }

    public async Task<IReadOnlyList<ContextMessage>> AppendAsync(
        Guid projectId, string role, string content, CancellationToken ct = default)
    {
        var db = _redis.GetDatabase();
        var msg = new ContextMessage(Guid.NewGuid(), role, content, DateTime.UtcNow);
        await db.ListRightPushAsync(Key(projectId), JsonSerializer.Serialize(msg));
        // Keep list bounded
        await db.ListTrimAsync(Key(projectId), -MaxMessages, -1);
        return await GetThreadAsync(projectId, ct);
    }

    public async Task ClearThreadAsync(Guid projectId, CancellationToken ct = default)
    {
        var db = _redis.GetDatabase();
        await db.KeyDeleteAsync(Key(projectId));
    }
}
