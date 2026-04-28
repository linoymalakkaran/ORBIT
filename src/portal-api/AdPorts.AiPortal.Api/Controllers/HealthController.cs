using Microsoft.AspNetCore.Mvc;
using Microsoft.Extensions.Diagnostics.HealthChecks;

namespace AdPorts.AiPortal.Api.Controllers;

[ApiController]
[Route("api")]
public class HealthController(HealthCheckService healthCheck) : ControllerBase
{
    [HttpGet("health")]
    public IActionResult Health() => Ok(new { status = "healthy", timestamp = DateTimeOffset.UtcNow });

    [HttpGet("version")]
    public IActionResult Version() => Ok(new
    {
        service  = "portal-api",
        version  = "1.0.0",
        build    = Environment.GetEnvironmentVariable("BUILD_SHA") ?? "local",
        timestamp = DateTimeOffset.UtcNow
    });
}
