namespace AdPorts.AiPortal.Domain.Entities;

public class TeamMember
{
    public Guid   Id          { get; private set; } = Guid.NewGuid();
    public Guid   ProjectId   { get; private set; }
    public Guid   UserId      { get; private set; }
    public string Role        { get; private set; } = default!;
    public bool   OptedIntoAutoImpl   { get; private set; }
    public string PrReviewMode        { get; private set; } = "advisory";
    public DateTimeOffset CreatedAt   { get; private set; } = DateTimeOffset.UtcNow;

    // Navigation
    public Project?    Project { get; private set; }
    public PortalUser? User    { get; private set; }

    private TeamMember() { }

    public static TeamMember Add(Guid projectId, Guid userId, string role)
    {
        if (!ValidRoles.Contains(role))
            throw new ArgumentException($"Invalid role '{role}'", nameof(role));
        return new TeamMember { ProjectId = projectId, UserId = userId, Role = role };
    }

    public void UpdateRole(string role)
    {
        if (!ValidRoles.Contains(role))
            throw new ArgumentException($"Invalid role '{role}'", nameof(role));
        Role = role;
    }

    private static readonly HashSet<string> ValidRoles =
        ["architect", "tech-lead", "developer", "qa", "sre", "observer"];
}
