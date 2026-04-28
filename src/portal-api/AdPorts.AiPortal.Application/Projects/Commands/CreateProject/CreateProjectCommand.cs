using AdPorts.AiPortal.Application.Common.Interfaces;
using AdPorts.AiPortal.Domain.Entities;
using FluentValidation;
using MediatR;
using Microsoft.EntityFrameworkCore;

namespace AdPorts.AiPortal.Application.Projects.Commands.CreateProject;

public record CreateProjectCommand(string Slug, string DisplayName, string? Program,
    string? Description) : IRequest<Guid>;

public class CreateProjectValidator : AbstractValidator<CreateProjectCommand>
{
    public CreateProjectValidator()
    {
        RuleFor(x => x.Slug).NotEmpty().MaximumLength(100).Matches(@"^[a-z0-9\-]+$");
        RuleFor(x => x.DisplayName).NotEmpty().MaximumLength(255);
        RuleFor(x => x.Program).MaximumLength(100).When(x => x.Program is not null);
    }
}

public class CreateProjectHandler(IPortalDbContext db, ICurrentUser currentUser)
    : IRequestHandler<CreateProjectCommand, Guid>
{
    public async Task<Guid> Handle(CreateProjectCommand cmd, CancellationToken ct)
    {
        var slugExists = await db.Projects.AnyAsync(p => p.Slug == cmd.Slug, ct);
        if (slugExists) throw new InvalidOperationException($"Slug '{cmd.Slug}' already exists.");

        var project = Project.Create(cmd.Slug, cmd.DisplayName, cmd.Program,
            cmd.Description, currentUser.Id);
        db.Add(project);
        await db.SaveChangesAsync(ct);
        return project.Id;
    }
}
