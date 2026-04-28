using AdPorts.AiPortal.Application.Common.Interfaces;
using AdPorts.AiPortal.Application.Projects.Commands.CreateProject;
using AdPorts.AiPortal.Application.Projects.Queries.GetProjects;
using MediatR;
using Microsoft.AspNetCore.Authorization;
using Microsoft.AspNetCore.Mvc;

namespace AdPorts.AiPortal.Api.Controllers;

[ApiController]
[Route("api/projects")]
[Authorize]
public class ProjectsController(IMediator mediator) : ControllerBase
{
    [HttpGet]
    public async Task<IActionResult> List(
        [FromQuery] string? program, [FromQuery] string? status,
        [FromQuery] int page = 1, [FromQuery] int pageSize = 20,
        CancellationToken ct = default)
    {
        var result = await mediator.Send(new GetProjectsQuery(program, status, page, pageSize), ct);
        return Ok(result);
    }

    [HttpGet("{id:guid}")]
    public async Task<IActionResult> Get(Guid id, CancellationToken ct)
    {
        var result = await mediator.Send(new Application.Projects.Queries.GetProjectById.GetProjectByIdQuery(id), ct);
        return result is null ? NotFound() : Ok(result);
    }

    [HttpPost]
    public async Task<IActionResult> Create([FromBody] CreateProjectCommand cmd, CancellationToken ct)
    {
        var id = await mediator.Send(cmd, ct);
        return CreatedAtAction(nameof(Get), new { id }, new { id });
    }

    [HttpPut("{id:guid}")]
    public async Task<IActionResult> Update(Guid id,
        [FromBody] Application.Projects.Commands.UpdateProject.UpdateProjectCommand cmd,
        CancellationToken ct)
    {
        await mediator.Send(cmd with { Id = id }, ct);
        return NoContent();
    }

    [HttpDelete("{id:guid}")]
    [Authorize(Roles = "portal:admin")]
    public async Task<IActionResult> Archive(Guid id, CancellationToken ct)
    {
        await mediator.Send(new Application.Projects.Commands.ArchiveProject.ArchiveProjectCommand(id), ct);
        return NoContent();
    }
}
