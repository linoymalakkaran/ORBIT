using MediatR;
using Microsoft.AspNetCore.Authorization;
using Microsoft.AspNetCore.Mvc;

namespace AdPorts.AiPortal.Api.Controllers;

[ApiController]
[Route("api/ledger")]
[Authorize]
public class LedgerController(IMediator mediator) : ControllerBase
{
    [HttpGet("projects/{projectId:guid}")]
    public async Task<IActionResult> ByProject(Guid projectId,
        [FromQuery] int? stage, [FromQuery] DateTimeOffset? from, [FromQuery] DateTimeOffset? to,
        [FromQuery] int page = 1, [FromQuery] int pageSize = 50,
        CancellationToken ct = default)
    {
        var result = await mediator.Send(
            new Application.Ledger.Queries.GetLedgerEntries.GetLedgerEntriesQuery(
                projectId, stage, from, to, page, pageSize), ct);
        return Ok(result);
    }

    [HttpGet("projects/{projectId:guid}/verify")]
    public async Task<IActionResult> VerifyChain(Guid projectId, CancellationToken ct)
    {
        var result = await mediator.Send(
            new Application.Ledger.Queries.VerifyChain.VerifyChainQuery(projectId), ct);
        return Ok(result);
    }
}
