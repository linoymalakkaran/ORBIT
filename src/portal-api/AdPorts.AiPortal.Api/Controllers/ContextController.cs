using MediatR;
using Microsoft.AspNetCore.Authorization;
using Microsoft.AspNetCore.Mvc;

namespace AdPorts.AiPortal.Api.Controllers;

[ApiController]
[Route("api/projects/{projectId:guid}/context")]
[Authorize]
public class ContextController(IMediator mediator) : ControllerBase
{
    [HttpGet]
    public async Task<IActionResult> GetSessions(Guid projectId, CancellationToken ct)
    {
        var result = await mediator.Send(
            new Application.Context.Queries.GetContextSessions.GetContextSessionsQuery(projectId), ct);
        return Ok(result);
    }

    [HttpGet("{sessionId}")]
    public async Task<IActionResult> GetTurns(Guid projectId, string sessionId, CancellationToken ct)
    {
        var result = await mediator.Send(
            new Application.Context.Queries.GetContextTurns.GetContextTurnsQuery(projectId, sessionId), ct);
        return Ok(result);
    }

    [HttpPost("{sessionId}/turns")]
    public async Task<IActionResult> AddTurn(Guid projectId, string sessionId,
        [FromBody] Application.Context.Commands.AddContextTurn.AddContextTurnCommand cmd,
        CancellationToken ct)
    {
        await mediator.Send(cmd with { ProjectId = projectId, SessionId = sessionId }, ct);
        return Accepted();
    }
}
