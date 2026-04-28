namespace AdPorts.AiPortal.Domain.Entities;

public class PortalUser
{
    public Guid     Id              { get; private set; }
    public string   Username        { get; private set; } = default!;
    public string   Email           { get; private set; } = default!;
    public string?  DisplayName     { get; private set; }
    public string[] KeycloakGroups  { get; private set; } = [];
    public DateTimeOffset? LastSeenAt  { get; private set; }
    public DateTimeOffset  CreatedAt   { get; private set; } = DateTimeOffset.UtcNow;

    private PortalUser() { }

    public static PortalUser CreateFromToken(Guid keycloakSubject, string username,
        string email, string? displayName, string[] groups)
    {
        return new PortalUser
        {
            Id             = keycloakSubject,
            Username       = username,
            Email          = email,
            DisplayName    = displayName,
            KeycloakGroups = groups
        };
    }

    public void RecordSeen()       => LastSeenAt = DateTimeOffset.UtcNow;
    public void UpdateGroups(string[] groups) => KeycloakGroups = groups;
}
