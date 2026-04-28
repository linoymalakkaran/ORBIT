using AdPorts.AiPortal.Application.Common.Interfaces;
using MediatR;
using Microsoft.EntityFrameworkCore;
using System.Security.Cryptography;
using System.Text;

namespace AdPorts.AiPortal.Application.Ledger.Queries.VerifyChain;

public record VerifyChainQuery(Guid ProjectId) : IRequest<VerifyChainResult>;

public record VerifyChainResult(bool Valid, int Checked, string? FailedAtEventId,
    string? ExpectedHash, string? ActualHash);

public class VerifyChainHandler(IPortalDbContext db) : IRequestHandler<VerifyChainQuery, VerifyChainResult>
{
    public async Task<VerifyChainResult> Handle(VerifyChainQuery q, CancellationToken ct)
    {
        var entries = await db.LedgerEntries.AsNoTracking()
            .Where(l => l.ProjectId == q.ProjectId)
            .OrderBy(l => l.OccurredAt)
            .ToListAsync(ct);

        string? previousHash = null;
        foreach (var entry in entries)
        {
            var computed = ComputeHash(entry.EventId, entry.EventData, previousHash);
            if (computed != entry.EntryHash)
                return new VerifyChainResult(false, entries.IndexOf(entry),
                    entry.EventId, computed, entry.EntryHash);
            previousHash = entry.EntryHash;
        }
        return new VerifyChainResult(true, entries.Count, null, null, null);
    }

    private static string ComputeHash(string eventId, string data, string? prevHash)
    {
        var raw = $"{eventId}|{data}|{prevHash ?? "genesis"}";
        return Convert.ToHexString(SHA256.HashData(Encoding.UTF8.GetBytes(raw))).ToLowerInvariant();
    }
}
