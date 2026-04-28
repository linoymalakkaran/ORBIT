namespace AdPorts.AiPortal.Domain.Entities;

public class Artifact
{
    public Guid   Id           { get; private set; } = Guid.NewGuid();
    public Guid   ProjectId    { get; private set; }
    public int    StageNumber  { get; private set; }
    public string StageName    { get; private set; } = default!;
    public string ArtifactType { get; private set; } = default!;
    public string Version      { get; private set; } = default!;
    public string StorageUri   { get; private set; } = default!;
    public string ContentHash  { get; private set; } = default!;
    public string Metadata     { get; private set; } = "{}";
    public DateTimeOffset CreatedAt  { get; private set; } = DateTimeOffset.UtcNow;
    public Guid?  CreatedBy    { get; private set; }
    public Guid?  SupersededBy { get; private set; }

    // Navigation
    public Project? Project { get; private set; }
    public ICollection<Approval> Approvals { get; private set; } = [];

    private Artifact() { }

    public static Artifact Create(Guid projectId, int stageNumber, string stageName,
        string artifactType, string version, string storageUri, string contentHash,
        Guid? createdBy, string? metadata = null)
    {
        ArgumentException.ThrowIfNullOrWhiteSpace(storageUri);
        ArgumentException.ThrowIfNullOrWhiteSpace(contentHash);
        return new Artifact
        {
            ProjectId    = projectId,
            StageNumber  = stageNumber,
            StageName    = stageName,
            ArtifactType = artifactType,
            Version      = version,
            StorageUri   = storageUri,
            ContentHash  = contentHash,
            CreatedBy    = createdBy,
            Metadata     = metadata ?? "{}"
        };
    }

    public void Supersede(Guid newArtifactId) => SupersededBy = newArtifactId;
}
