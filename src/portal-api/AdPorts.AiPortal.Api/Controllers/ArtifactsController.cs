using MediatR;
using Microsoft.AspNetCore.Authorization;
using Microsoft.AspNetCore.Mvc;

namespace AdPorts.AiPortal.Api.Controllers;

[ApiController]
[Route("api/projects/{projectId:guid}/artifacts")]
[Authorize]
public class ArtifactsController(IMediator mediator) : ControllerBase
{
    [HttpGet]
    public async Task<IActionResult> List(Guid projectId, [FromQuery] int? stage, CancellationToken ct)
    {
        var result = await mediator.Send(
            new Application.Artifacts.Queries.GetArtifacts.GetArtifactsQuery(projectId, stage), ct);
        return Ok(result);
    }

    [HttpGet("{id:guid}")]
    public async Task<IActionResult> Get(Guid projectId, Guid id, CancellationToken ct)
    {
        var result = await mediator.Send(
            new Application.Artifacts.Queries.GetArtifactById.GetArtifactByIdQuery(id), ct);
        return result is null ? NotFound() : Ok(result);
    }

    [HttpPost]
    public async Task<IActionResult> Upload(Guid projectId,
        [FromBody] Application.Artifacts.Commands.UploadArtifact.UploadArtifactCommand cmd,
        CancellationToken ct)
    {
        var id = await mediator.Send(cmd with { ProjectId = projectId }, ct);
        return CreatedAtAction(nameof(Get), new { projectId, id }, new { id });
    }
}
