using Microsoft.AspNetCore.Authorization;
using Microsoft.AspNetCore.Mvc;

namespace AdPorts.AiPortal.Api.Controllers;

/// <summary>Admin endpoints — stubs returning 501 until Phase 07/08</summary>
[ApiController]
[Route("api/admin")]
[Authorize(Roles = "portal:admin")]
public class AdminController : ControllerBase
{
    [HttpGet("skills")]
    public IActionResult ListSkills() =>
        StatusCode(StatusCodes.Status501NotImplemented, new { message = "Implemented in Phase 07" });

    [HttpGet("mcps")]
    public IActionResult ListMcps() =>
        StatusCode(StatusCodes.Status501NotImplemented, new { message = "Implemented in Phase 08" });

    [HttpGet("agents")]
    public IActionResult ListAgents() =>
        StatusCode(StatusCodes.Status501NotImplemented, new { message = "Implemented in Phase 10" });

    [HttpGet("fleet")]
    public IActionResult ListFleet() =>
        StatusCode(StatusCodes.Status501NotImplemented, new { message = "Implemented in Phase 15" });
}
