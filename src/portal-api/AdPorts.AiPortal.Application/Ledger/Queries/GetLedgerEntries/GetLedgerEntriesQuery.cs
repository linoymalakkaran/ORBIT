using AdPorts.AiPortal.Application.Common.Interfaces;
using MediatR;
using Microsoft.EntityFrameworkCore;
using System.Security.Cryptography;
using System.Text;
using System.Text.Json;

namespace AdPorts.AiPortal.Application.Ledger.Queries.GetLedgerEntries;

public record GetLedgerEntriesQuery(Guid ProjectId, int? Stage, DateTimeOffset? From,
    DateTimeOffset? To, int Page, int PageSize) : IRequest<LedgerEntriesResult>;

public record LedgerEntriesResult(IReadOnlyList<LedgerEntryDto> Items, int Total);

public record LedgerEntryDto(Guid Id, string EventType, Guid? ActorId, string EventData,
    string? EntryHash, string? PreviousHash, DateTimeOffset OccurredAt, int? StageNumber);

public class GetLedgerEntriesHandler(IPortalDbContext db)
    : IRequestHandler<GetLedgerEntriesQuery, LedgerEntriesResult>
{
    public async Task<LedgerEntriesResult> Handle(GetLedgerEntriesQuery q, CancellationToken ct)
    {
        var query = db.LedgerEntries.AsNoTracking().Where(l => l.ProjectId == q.ProjectId);
        if (q.Stage.HasValue) query = query.Where(l => l.StageNumber == q.Stage);
        if (q.From.HasValue)  query = query.Where(l => l.OccurredAt >= q.From);
        if (q.To.HasValue)    query = query.Where(l => l.OccurredAt <= q.To);

        var total = await query.CountAsync(ct);
        var items = await query
            .OrderBy(l => l.OccurredAt)
            .Skip((q.Page - 1) * q.PageSize).Take(q.PageSize)
            .Select(l => new LedgerEntryDto(l.Id, l.EventType, l.ActorId, l.EventData,
                l.EntryHash, l.PreviousHash, l.OccurredAt, l.StageNumber))
            .ToListAsync(ct);

        return new LedgerEntriesResult(items, total);
    }
}
