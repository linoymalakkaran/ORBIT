using AdPorts.AiPortal.Domain.Entities;
using Microsoft.EntityFrameworkCore;
using Microsoft.EntityFrameworkCore.Metadata.Builders;

namespace AdPorts.AiPortal.Infrastructure.Persistence.Configurations;

public class ProjectConfiguration : IEntityTypeConfiguration<Project>
{
    public void Configure(EntityTypeBuilder<Project> b)
    {
        b.ToTable("projects");
        b.HasKey(p => p.Id);
        b.Property(p => p.Slug).HasMaxLength(100).IsRequired();
        b.HasIndex(p => p.Slug).IsUnique();
        b.Property(p => p.DisplayName).HasMaxLength(255).IsRequired();
        b.Property(p => p.Program).HasMaxLength(100);
        b.Property(p => p.Status).HasMaxLength(50).IsRequired().HasDefaultValue("active");
        b.Property(p => p.ComplianceScope).HasColumnType("jsonb").HasDefaultValue("[]");
        b.Property(p => p.StackFingerprint).HasColumnType("jsonb");
        b.Property(p => p.IntegrationMap).HasColumnType("jsonb").HasDefaultValue("[]");
        b.Property(p => p.DeploymentState).HasColumnType("jsonb").HasDefaultValue("{}");
        b.HasMany(p => p.TeamMembers).WithOne(t => t.Project).HasForeignKey(t => t.ProjectId);
        b.HasMany(p => p.Artifacts).WithOne(a => a.Project).HasForeignKey(a => a.ProjectId);
        b.HasMany(p => p.LedgerEntries).WithOne(l => l.Project).HasForeignKey(l => l.ProjectId);
    }
}

public class PortalUserConfiguration : IEntityTypeConfiguration<PortalUser>
{
    public void Configure(EntityTypeBuilder<PortalUser> b)
    {
        b.ToTable("users");
        b.HasKey(u => u.Id);
        b.Property(u => u.Username).HasMaxLength(100).IsRequired();
        b.HasIndex(u => u.Username).IsUnique();
        b.Property(u => u.Email).HasMaxLength(255).IsRequired();
        b.Property(u => u.DisplayName).HasMaxLength(255);
        b.Property(u => u.KeycloakGroups).HasColumnType("text[]").HasDefaultValue(Array.Empty<string>());
    }
}

public class TeamMemberConfiguration : IEntityTypeConfiguration<TeamMember>
{
    public void Configure(EntityTypeBuilder<TeamMember> b)
    {
        b.ToTable("teams");
        b.HasKey(t => t.Id);
        b.Property(t => t.Role).HasMaxLength(50).IsRequired();
        b.Property(t => t.PrReviewMode).HasMaxLength(20).HasDefaultValue("advisory");
        b.HasIndex(t => new { t.ProjectId, t.UserId }).IsUnique();
        b.HasOne(t => t.Project).WithMany(p => p.TeamMembers).HasForeignKey(t => t.ProjectId);
        b.HasOne(t => t.User).WithMany().HasForeignKey(t => t.UserId);
    }
}

public class ArtifactConfiguration : IEntityTypeConfiguration<Artifact>
{
    public void Configure(EntityTypeBuilder<Artifact> b)
    {
        b.ToTable("artifacts");
        b.HasKey(a => a.Id);
        b.Property(a => a.StageName).HasMaxLength(100).IsRequired();
        b.Property(a => a.ArtifactType).HasMaxLength(100).IsRequired();
        b.Property(a => a.Version).HasMaxLength(20).IsRequired();
        b.Property(a => a.ContentHash).HasMaxLength(64).IsRequired();
        b.Property(a => a.Metadata).HasColumnType("jsonb").HasDefaultValue("{}");
        b.HasOne(a => a.Project).WithMany(p => p.Artifacts).HasForeignKey(a => a.ProjectId);
    }
}

public class ApprovalConfiguration : IEntityTypeConfiguration<Approval>
{
    public void Configure(EntityTypeBuilder<Approval> b)
    {
        b.ToTable("approvals");
        b.HasKey(a => a.Id);
        b.Property(a => a.Decision).HasMaxLength(20).IsRequired();
        b.Property(a => a.ArtifactHashes).HasColumnType("jsonb").IsRequired();
        b.HasOne(a => a.Artifact).WithMany(ar => ar.Approvals).HasForeignKey(a => a.ArtifactId);
    }
}

public class LedgerEntryConfiguration : IEntityTypeConfiguration<LedgerEntry>
{
    public void Configure(EntityTypeBuilder<LedgerEntry> b)
    {
        b.ToTable("ledger_entries");
        b.HasKey(l => l.Id);
        b.Property(l => l.StreamId).HasMaxLength(255).IsRequired();
        b.Property(l => l.EventId).HasMaxLength(255).IsRequired();
        b.HasIndex(l => l.EventId).IsUnique();
        b.Property(l => l.EventType).HasMaxLength(100).IsRequired();
        b.Property(l => l.RiskTier).HasMaxLength(20);
        b.Property(l => l.ArtifactIds).HasColumnType("uuid[]").HasDefaultValue(Array.Empty<Guid>());
        b.Property(l => l.JiraRefs).HasColumnType("text[]").HasDefaultValue(Array.Empty<string>());
        b.Property(l => l.ComplianceTags).HasColumnType("text[]").HasDefaultValue(Array.Empty<string>());
        b.Property(l => l.EventData).HasColumnType("jsonb").IsRequired();
        b.Property(l => l.PreviousHash).HasMaxLength(64);
        b.Property(l => l.EntryHash).HasMaxLength(64);
        b.HasIndex(l => l.EntryHash).IsUnique();
        b.HasOne(l => l.Project).WithMany(p => p.LedgerEntries).HasForeignKey(l => l.ProjectId);
        b.HasIndex(l => new { l.ProjectId, l.OccurredAt });
        b.HasIndex(l => new { l.ProjectId, l.StageNumber });
        b.HasIndex(l => new { l.ActorId, l.OccurredAt });
    }
}
