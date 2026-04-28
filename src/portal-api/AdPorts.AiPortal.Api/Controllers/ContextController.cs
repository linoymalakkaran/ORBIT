using MediatR;
using Microsoft.AspNetCore.Authorization;
using Microsoft.AspNetCore.Mvc;
using AdPorts.AiPortal.Application.Context.Queries.GetContextThread;
using AdPorts.AiPortal.Application.Context.Commands.AppendContext;
using AdPorts.AiPortal.Application.Context.Commands.ClearContext;

namespace AdPorts.AiPortal.Api.Controllers;

[ApiController]
[Route("api/context/{projectId:guid}")]
[Authorize]
public class ContextController(IMediator mediator) : ControllerBase
{
    [HttpGet]
    public async Task<IActionResult> GetThread(Guid projectId, CancellationToken ct)
    {
        var result = await mediator.Send(new GetContextThreadQuery(projectId), ct);
        return Ok(result);
    }

    [HttpPost]
    public async Task<IActionResult> Append(Guid projectId,
        [FromBody] AppendRequest body, CancellationToken ct)
    {
        var result = await mediator.Send(
            new AppendContextCommand(projectId, body.Role ?? "user", body.Message), ct);
        return Ok(result);
    }

    [HttpDelete]
    public async Task<IActionResult> Clear(Guid projectId, CancellationToken ct)
    {
        await mediator.Send(new ClearContextCommand(projectId), ct);
        return NoContent();
    }
}

public record AppendRequest(string Message, string? Role);

