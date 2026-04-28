using AdPorts.AiPortal.Application.Common.Interfaces;
using AdPorts.AiPortal.Domain.Entities;
using FluentValidation;
using MediatR;
using Microsoft.EntityFrameworkCore;

namespace AdPorts.AiPortal.Application.Approvals.Commands.SubmitApproval;

public record SubmitApprovalCommand(
    Guid   ArtifactId,
    string Decision,
    string? Comment,
    string ArtifactHashesJson,
    string? Signature = null) : IRequest<Guid>;

public class SubmitApprovalValidator : AbstractValidator<SubmitApprovalCommand>
{
    private static readonly string[] ValidDecisions = ["approved", "rejected", "changes-requested"];
    public SubmitApprovalValidator()
    {
        RuleFor(x => x.Decision).NotEmpty().Must(d => ValidDecisions.Contains(d))
            .WithMessage("Decision must be approved, rejected, or changes-requested");
    }
}

public class SubmitApprovalHandler(IPortalDbContext db, ICurrentUser currentUser,
    IAuthorizationService authz) : IRequestHandler<SubmitApprovalCommand, Guid>
{
    public async Task<Guid> Handle(SubmitApprovalCommand cmd, CancellationToken ct)
    {
        var artifact = await db.Artifacts
            .FirstOrDefaultAsync(a => a.Id == cmd.ArtifactId, ct)
            ?? throw new KeyNotFoundException($"Artifact {cmd.ArtifactId} not found");

        // OpenFGA check: user must have can_approve on the project
        var allowed = await authz.CheckAsync(
            $"user:{currentUser.Id}", "can_approve", $"project:{artifact.ProjectId}", ct);
        if (!allowed)
            throw new UnauthorizedAccessException("User does not have approval rights on this project");

        var approval = Approval.Create(cmd.ArtifactId, currentUser.Id, cmd.Decision,
            cmd.Comment, cmd.ArtifactHashesJson, cmd.Signature);
        db.Add(approval);
        await db.SaveChangesAsync(ct);
        return approval.Id;
    }
}
