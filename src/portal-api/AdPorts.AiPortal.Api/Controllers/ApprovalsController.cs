using MediatR;
using Microsoft.AspNetCore.Authorization;
using Microsoft.AspNetCore.Mvc;

namespace AdPorts.AiPortal.Api.Controllers;

[ApiController]
[Route("api/artifacts/{artifactId:guid}/approvals")]
[Authorize]
public class ApprovalsController(IMediator mediator) : ControllerBase
{
    [HttpGet]
    public async Task<IActionResult> List(Guid artifactId, CancellationToken ct)
    {
        var result = await mediator.Send(
            new Application.Approvals.Queries.GetApprovals.GetApprovalsQuery(artifactId), ct);
        return Ok(result);
    }

    [HttpPost]
    public async Task<IActionResult> Submit(Guid artifactId,
        [FromBody] Application.Approvals.Commands.SubmitApproval.SubmitApprovalCommand cmd,
        CancellationToken ct)
    {
        var id = await mediator.Send(cmd with { ArtifactId = artifactId }, ct);
        return CreatedAtAction(nameof(List), new { artifactId }, new { id });
    }
}
