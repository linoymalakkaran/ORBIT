using AdPorts.AiPortal.Application.Common.Interfaces;
using AdPorts.AiPortal.Domain.Entities;
using Microsoft.EntityFrameworkCore;

namespace AdPorts.AiPortal.Infrastructure.Persistence;

public class PortalDbContext(DbContextOptions<PortalDbContext> options) : DbContext(options), IPortalDbContext
{
    public DbSet<Project>     ProjectSet     { get; set; } = default!;
    public DbSet<PortalUser>  UserSet        { get; set; } = default!;
    public DbSet<TeamMember>  TeamMemberSet  { get; set; } = default!;
    public DbSet<Artifact>    ArtifactSet    { get; set; } = default!;
    public DbSet<Approval>    ApprovalSet    { get; set; } = default!;
    public DbSet<LedgerEntry> LedgerEntrySet { get; set; } = default!;

    // IPortalDbContext
    public IQueryable<Project>     Projects      => ProjectSet.AsQueryable();
    public IQueryable<PortalUser>  Users         => UserSet.AsQueryable();
    public IQueryable<TeamMember>  TeamMembers   => TeamMemberSet.AsQueryable();
    public IQueryable<Artifact>    Artifacts     => ArtifactSet.AsQueryable();
    public IQueryable<Approval>    Approvals     => ApprovalSet.AsQueryable();
    public IQueryable<LedgerEntry> LedgerEntries => LedgerEntrySet.AsQueryable();

    void IPortalDbContext.Add<T>(T entity)    => base.Add(entity);
    void IPortalDbContext.Remove<T>(T entity) => base.Remove(entity);

    protected override void OnModelCreating(ModelBuilder mb)
    {
        mb.ApplyConfigurationsFromAssembly(typeof(PortalDbContext).Assembly);
        base.OnModelCreating(mb);
    }
}
