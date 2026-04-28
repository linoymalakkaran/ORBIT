using AdPorts.AiPortal.Application.Common.Interfaces;
using FluentValidation;
using MediatR;
using Microsoft.EntityFrameworkCore;

namespace AdPorts.AiPortal.Application.Projects.Commands.UpdateProject;

public record UpdateProjectCommand(Guid Id, string DisplayName, string? Description, string? Program)
    : IRequest;

public class UpdateProjectValidator : AbstractValidator<UpdateProjectCommand>
{
    public UpdateProjectValidator()
    {
        RuleFor(x => x.DisplayName).NotEmpty().MaximumLength(255);
    }
}

public class UpdateProjectHandler(IPortalDbContext db) : IRequestHandler<UpdateProjectCommand>
{
    public async Task Handle(UpdateProjectCommand cmd, CancellationToken ct)
    {
        var project = await db.Projects.IgnoreQueryFilters()
            .FirstOrDefaultAsync(p => p.Id == cmd.Id, ct)
            ?? throw new KeyNotFoundException($"Project {cmd.Id} not found");
        project.Update(cmd.DisplayName, cmd.Description, cmd.Program);
        await db.SaveChangesAsync(ct);
    }
}
