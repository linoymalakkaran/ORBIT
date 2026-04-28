namespace AdPorts.AiPortal.Domain.Entities;

public class Approval
{
    public Guid   Id              { get; private set; } = Guid.NewGuid();
    public Guid   ArtifactId      { get; private set; }
    public Guid   ApproverId      { get; private set; }
    public string Decision        { get; private set; } = default!;
    public string? Comment        { get; private set; }
    public string? Signature      { get; private set; }
    public string ArtifactHashes  { get; private set; } = "{}";
    public DateTimeOffset CreatedAt { get; private set; } = DateTimeOffset.UtcNow;

    // Navigation
    public Artifact?    Artifact { get; private set; }
    public PortalUser?  Approver { get; private set; }

    private Approval() { }

    public static Approval Create(Guid artifactId, Guid approverId, string decision,
        string? comment, string artifactHashesJson, string? signature = null)
    {
        if (!ValidDecisions.Contains(decision))
            throw new ArgumentException($"Invalid decision '{decision}'", nameof(decision));
        return new Approval
        {
            ArtifactId     = artifactId,
            ApproverId     = approverId,
            Decision       = decision,
            Comment        = comment,
            Signature      = signature,
            ArtifactHashes = artifactHashesJson
        };
    }

    private static readonly HashSet<string> ValidDecisions =
        ["approved", "rejected", "changes-requested"];
}
