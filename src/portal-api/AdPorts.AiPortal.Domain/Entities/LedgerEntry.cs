namespace AdPorts.AiPortal.Domain.Entities;

public class LedgerEntry
{
    public Guid   Id             { get; private set; } = Guid.NewGuid();
    public string StreamId       { get; private set; } = default!;
    public string EventId        { get; private set; } = default!;
    public string EventType      { get; private set; } = default!;
    public Guid?  ProjectId      { get; private set; }
    public int?   StageNumber    { get; private set; }
    public Guid?  ActorId        { get; private set; }
    public Guid[] ArtifactIds    { get; private set; } = [];
    public string[] JiraRefs     { get; private set; } = [];
    public string? RiskTier      { get; private set; }
    public string[] ComplianceTags { get; private set; } = [];
    public string EventData      { get; private set; } = "{}";
    public string? PreviousHash  { get; private set; }
    public string? EntryHash     { get; private set; }
    public DateTimeOffset OccurredAt  { get; private set; }
    public DateTimeOffset RecordedAt  { get; private set; } = DateTimeOffset.UtcNow;

    // Navigation
    public Project? Project { get; private set; }

    private LedgerEntry() { }

    public static LedgerEntry Create(string streamId, string eventId, string eventType,
        Guid? projectId, Guid? actorId, string eventDataJson,
        string? previousHash, string entryHash,
        DateTimeOffset occurredAt, int? stageNumber = null)
    {
        return new LedgerEntry
        {
            StreamId     = streamId,
            EventId      = eventId,
            EventType    = eventType,
            ProjectId    = projectId,
            ActorId      = actorId,
            EventData    = eventDataJson,
            PreviousHash = previousHash,
            EntryHash    = entryHash,
            OccurredAt   = occurredAt,
            StageNumber  = stageNumber
        };
    }
}
