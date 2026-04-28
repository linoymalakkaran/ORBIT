using AdPorts.AiPortal.Domain.Entities;

namespace AdPorts.AiPortal.Application.Common.Interfaces;

public interface IPortalDbContext
{
    IQueryable<Project>     Projects     { get; }
    IQueryable<PortalUser>  Users        { get; }
    IQueryable<TeamMember>  TeamMembers  { get; }
    IQueryable<Artifact>    Artifacts    { get; }
    IQueryable<Approval>    Approvals    { get; }
    IQueryable<LedgerEntry> LedgerEntries { get; }

    Task<int> SaveChangesAsync(CancellationToken cancellationToken = default);

    void Add<T>(T entity) where T : class;
    void Remove<T>(T entity) where T : class;
}
