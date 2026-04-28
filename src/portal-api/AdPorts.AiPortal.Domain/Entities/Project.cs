namespace AdPorts.AiPortal.Domain.Entities;

public class Project
{
    public Guid   Id              { get; private set; } = Guid.NewGuid();
    public string Slug            { get; private set; } = default!;
    public string DisplayName     { get; private set; } = default!;
    public string? Program        { get; private set; }
    public string? Description    { get; private set; }
    public string Status          { get; private set; } = "active";
    public string ComplianceScope { get; private set; } = "[]";     // JSONB
    public string? StackFingerprint { get; private set; }           // JSONB
    public string IntegrationMap  { get; private set; } = "[]";     // JSONB
    public string DeploymentState { get; private set; } = "{}";     // JSONB
    public DateTimeOffset CreatedAt { get; private set; } = DateTimeOffset.UtcNow;
    public DateTimeOffset UpdatedAt { get; private set; } = DateTimeOffset.UtcNow;
    public Guid?  CreatedBy       { get; private set; }

    // Navigation
    public ICollection<TeamMember> TeamMembers { get; private set; } = [];
    public ICollection<Artifact>   Artifacts   { get; private set; } = [];
    public ICollection<LedgerEntry> LedgerEntries { get; private set; } = [];

    private Project() { }

    public static Project Create(string slug, string displayName, string? program,
        string? description, Guid? createdBy)
    {
        ArgumentException.ThrowIfNullOrWhiteSpace(slug);
        ArgumentException.ThrowIfNullOrWhiteSpace(displayName);
        return new Project
        {
            Slug        = slug.ToLowerInvariant(),
            DisplayName = displayName,
            Program     = program,
            Description = description,
            CreatedBy   = createdBy
        };
    }

    public void Update(string displayName, string? description, string? program)
    {
        DisplayName = displayName;
        Description = description;
        Program     = program;
        UpdatedAt   = DateTimeOffset.UtcNow;
    }

    public void SetStatus(string status)
    {
        Status    = status;
        UpdatedAt = DateTimeOffset.UtcNow;
    }
}
