# Instructions — Phase 03: Portal Backend API (CQRS .NET)

> Add this file to your IDE's custom instructions when building the Portal Backend API.

---

## Context

You are building the **AD Ports AI Portal Backend API** — a .NET 9 CQRS service that is the API gateway for the entire Portal. All Portal UI interactions, CLI commands, and agent-to-Portal communication go through this API. It uses Clean Architecture with CQRS (MediatR + FluentValidation + EF Core + OpenFGA).

---

## Project Structure

```
src/
├── AdPorts.Portal.Api/               ← ASP.NET Core 9 host
│   ├── Controllers/                  ← Thin controllers (1 method per endpoint)
│   ├── Middleware/                   ← Auth, exception handling, OTEL
│   └── Program.cs                    ← DI composition root
├── AdPorts.Portal.Application/       ← CQRS handlers, validators, DTOs
│   ├── Projects/
│   │   ├── Commands/
│   │   └── Queries/
│   ├── Artifacts/
│   ├── Approvals/
│   └── Behaviours/                   ← MediatR pipeline behaviours
├── AdPorts.Portal.Domain/            ← Entities, events, value objects (no framework refs)
├── AdPorts.Portal.Infrastructure/   ← DbContext, migrations, external clients
│   ├── Persistence/
│   ├── Ledger/
│   └── ExternalServices/
├── AdPorts.Portal.UnitTests/
└── AdPorts.Portal.IntegrationTests/
```

## API Design Conventions

- **All endpoints return `ProblemDetails`** (RFC 7807) for errors — not custom error objects.
- **Pagination uses cursor-based pagination** for large lists (ledger events, audit logs) and offset-based for smaller lists (projects, users).
- **All write operations** must produce a Pipeline Ledger event — never skip this.
- **No business logic in controllers** — controllers call MediatR and return the result.

```csharp
// CORRECT — thin controller pattern
[HttpPost]
[ProducesResponseType(typeof(CreateProjectResponse), 201)]
[ProducesResponseType(typeof(ProblemDetails), 400)]
[ProducesResponseType(typeof(ProblemDetails), 403)]
public async Task<IActionResult> CreateProject(
    [FromBody] CreateProjectRequest request,
    CancellationToken ct)
{
    var command = new CreateProjectCommand(
        request.Name,
        request.Domain,
        request.Description,
        User.GetUserId());

    var result = await _mediator.Send(command, ct);
    return result.IsSuccess
        ? CreatedAtAction(nameof(GetProject), new { id = result.Value }, result.Value)
        : result.ToProblemDetails();
}

// WRONG — business logic in controller
[HttpPost]
public async Task<IActionResult> CreateProject([FromBody] CreateProjectRequest request)
{
    if (string.IsNullOrEmpty(request.Name))  // FORBIDDEN — use FluentValidation
        return BadRequest("Name is required");
    ...
}
```

## Authorization Pattern (OpenFGA)

```csharp
// ALWAYS check OpenFGA permission — never rely solely on Keycloak roles for resource-level authz
public class GetProjectByIdQueryHandler : IRequestHandler<GetProjectByIdQuery, Result<ProjectDto>>
{
    private readonly IOpenFgaClient _fga;

    public async Task<Result<ProjectDto>> Handle(GetProjectByIdQuery request, CancellationToken ct)
    {
        // OpenFGA check: can this user read this specific project?
        var canRead = await _fga.CheckAsync(new CheckRequest
        {
            User     = $"user:{request.CurrentUserId}",
            Relation = "reader",
            Object   = $"project:{request.ProjectId}",
        }, ct);

        if (!canRead)
            return Result.Failure<ProjectDto>(Error.Forbidden("You do not have access to this project"));
        
        // ... proceed with data retrieval
    }
}
```

## Pipeline Ledger Integration (Mandatory)

Every command handler that changes state MUST record a Ledger event.

```csharp
public async Task<Result<Guid>> Handle(CreateProjectCommand request, CancellationToken ct)
{
    var project = Project.Create(request.Name, request.Domain, request.CreatedBy);
    _context.Projects.Add(project);
    await _context.SaveChangesAsync(ct);

    // MANDATORY — every state change produces a Ledger event
    await _ledger.RecordAsync(new LedgerEvent
    {
        EventType = "portal.project.created",
        ProjectId = project.Id,
        ActorId   = request.CreatedBy,
        EventData = new { project.Name, project.Domain },
    }, ct);

    return Result.Success(project.Id);
}
```

## EF Core Rules

- Use `AsNoTracking()` for all read-only queries.
- Pass `CancellationToken` to every `SaveChangesAsync` and `ToListAsync`.
- Column names in snake_case (EF Core `UseSnakeCaseNamingConvention()`).
- Migrations live in `AdPorts.Portal.Infrastructure/Persistence/Migrations/`.
- Never call `Database.EnsureCreated()` in production — use migration-based upgrades only.

## OpenTelemetry Requirements

```csharp
// Every handler adds activity tags for distributed tracing
using var activity = _activitySource.StartActivity("portal.project.create");
activity?.SetTag("project.id", project.Id.ToString());
activity?.SetTag("project.domain", project.Domain);
activity?.SetTag("actor.id", request.CreatedBy);
```

## Forbidden Patterns

| Pattern | Reason |
|---------|--------|
| `context.Database.ExecuteSqlRaw()` with unsanitized input | SQL injection risk — use parameterised EF Core queries |
| `new HttpClient()` directly | Use `IHttpClientFactory` — prevents socket exhaustion |
| `Thread.Sleep()` | Use `await Task.Delay()` — never block thread pool |
| Catching and swallowing `Exception` | Use MediatR exception behaviour — let it propagate |
| Storing secrets in `appsettings.json` | Use Vault Agent Injector — no secrets in config files |
| `[AllowAnonymous]` on non-health-check endpoints | All endpoints require auth unless explicitly public |

---

*Instructions — Phase 03 — AD Ports AI Portal — Applies to: Core Squad*
