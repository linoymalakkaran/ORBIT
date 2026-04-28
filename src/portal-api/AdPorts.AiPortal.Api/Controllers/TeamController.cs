using MediatR;
using Microsoft.AspNetCore.Authorization;
using Microsoft.AspNetCore.Mvc;

namespace AdPorts.AiPortal.Api.Controllers;

[ApiController]
[Route("api/projects/{projectId:guid}/team")]
[Authorize]
public class TeamController(IMediator mediator) : ControllerBase
{
    [HttpGet]
    public async Task<IActionResult> List(Guid projectId, CancellationToken ct)
    {
        var result = await mediator.Send(
            new Application.Team.Queries.GetTeam.GetTeamQuery(projectId), ct);
        return Ok(result);
    }

    [HttpPost]
    public async Task<IActionResult> AddMember(Guid projectId,
        [FromBody] Application.Team.Commands.AddTeamMember.AddTeamMemberCommand cmd,
        CancellationToken ct)
    {
        var id = await mediator.Send(cmd with { ProjectId = projectId }, ct);
        return CreatedAtAction(nameof(List), new { projectId }, new { id });
    }

    [HttpDelete("{userId:guid}")]
    public async Task<IActionResult> RemoveMember(Guid projectId, Guid userId, CancellationToken ct)
    {
        await mediator.Send(
            new Application.Team.Commands.RemoveTeamMember.RemoveTeamMemberCommand(projectId, userId), ct);
        return NoContent();
    }

    [HttpPut("{userId:guid}/role")]
    public async Task<IActionResult> UpdateRole(Guid projectId, Guid userId,
        [FromBody] Application.Team.Commands.UpdateTeamMemberRole.UpdateTeamMemberRoleCommand cmd,
        CancellationToken ct)
    {
        await mediator.Send(cmd with { ProjectId = projectId, UserId = userId }, ct);
        return NoContent();
    }
}
