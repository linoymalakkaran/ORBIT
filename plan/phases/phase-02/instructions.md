# Instructions — Phase 02: Core Data Layer & Identity

> Add this file to your IDE's custom instructions when working on Portal backend C# code, database schema, or OpenFGA authorization.

---

## Context

You are building the **AD Ports AI Portal backend** — a .NET 9 CQRS application. The Portal's database is PostgreSQL 16. Authorization is handled by OpenFGA. Identity is Keycloak 25 with JWT Bearer tokens. All C# code follows the AD Ports CQRS pattern (MediatR + FluentValidation + EF Core).

---

## C# Coding Standards

### CQRS Pattern

All business operations go through MediatR. Follow this pattern:

```csharp
// CORRECT — Query with validation
public record GetProjectByIdQuery(Guid ProjectId) : IRequest<ProjectDto>;

public class GetProjectByIdQueryValidator : AbstractValidator<GetProjectByIdQuery>
{
    public GetProjectByIdQueryValidator()
    {
        RuleFor(x => x.ProjectId).NotEmpty();
    }
}

public class GetProjectByIdQueryHandler(IPortalDbContext db, IAuthorizationService auth)
    : IRequestHandler<GetProjectByIdQuery, ProjectDto>
{
    public async Task<ProjectDto> Handle(GetProjectByIdQuery request, CancellationToken ct)
    {
        await auth.RequireAsync(PortalPermission.CanRead, $"project:{request.ProjectId}", ct);
        var project = await db.Projects
            .AsNoTracking()
            .FirstOrDefaultAsync(p => p.Id == request.ProjectId, ct)
            ?? throw new NotFoundException(nameof(Project), request.ProjectId);
        return project.ToDto();
    }
}
```

### Naming Conventions

- Commands: `VerbNounCommand` (e.g., `CreateProjectCommand`, `ApproveArtifactCommand`)
- Queries: `GetNounQuery` or `ListNounsQuery`
- Handlers: suffix `Handler`
- Validators: suffix `Validator`
- DTOs: suffix `Dto`
- Exceptions: use `NotFoundException`, `ForbiddenException`, `ValidationException`

### Entity Rules

- Domain entities are immutable records or classes with private setters.
- No public parameterless constructors on domain entities.
- `Id` property is always `Guid` (not `int`).
- All timestamps are `DateTimeOffset` in UTC — never `DateTime`.
- Use `UpdatedAt` trigger in Postgres, not application-level.

### EF Core Rules

- `AsNoTracking()` on all queries — only track when writing.
- Never call `SaveChanges` inside a loop.
- Always include `CancellationToken` on all async operations.
- Database column names are snake_case; C# properties are PascalCase.

```csharp
// CORRECT — EF Core configuration
public class ProjectConfiguration : IEntityTypeConfiguration<Project>
{
    public void Configure(EntityTypeBuilder<Project> builder)
    {
        builder.ToTable("projects");
        builder.HasKey(x => x.Id);
        builder.Property(x => x.Id).HasColumnName("id");
        builder.Property(x => x.Slug).HasColumnName("slug").HasMaxLength(100).IsRequired();
        builder.Property(x => x.StackFingerprint).HasColumnName("stack_fingerprint")
            .HasColumnType("jsonb");
        builder.Property(x => x.CreatedAt).HasColumnName("created_at")
            .HasDefaultValueSql("now()");
    }
}
```

### Error Handling

```csharp
// Global exception middleware handles these
public class NotFoundException(string entityName, object key)
    : Exception($"{entityName} with key '{key}' was not found.");

public class ForbiddenException(string action, string resource)
    : Exception($"You do not have permission to {action} on {resource}.");
```

### Dependency Injection

- Register services with the correct lifetime (Scoped for DbContext, Singleton for caches).
- Use `IOptions<TOptions>` pattern for configuration — never inject `IConfiguration` directly.
- All services are registered in `DependencyInjection.cs` in the Infrastructure project.

---

## OpenFGA Authorization Pattern

Always check authorization before business logic:

```csharp
public interface IPortalAuthorizationService
{
    Task RequireAsync(PortalPermission permission, string resourceKey, CancellationToken ct);
    Task<bool> CheckAsync(PortalPermission permission, string resourceKey, CancellationToken ct);
}

public enum PortalPermission
{
    CanRead,
    CanWrite,
    CanApprove,
    CanManageFleet,
    CanAdminister
}

// Usage in handler:
await auth.RequireAsync(PortalPermission.CanApprove, $"project:{projectId}", ct);
```

---

## Database Migrations

Always use EF Core migrations for schema changes:

```bash
# Add a new migration
cd src
dotnet ef migrations add AddNewFeature --project AdPorts.AiPortal.Infrastructure --startup-project AdPorts.AiPortal.Api

# Generate SQL script for review (MANDATORY before applying)
dotnet ef migrations script --idempotent --output migrations/$(date +%Y%m%d)_migration.sql

# Apply to dev
dotnet ef database update --project AdPorts.AiPortal.Infrastructure --startup-project AdPorts.AiPortal.Api
```

**Never** modify an existing migration — always add a new one.

---

## Observability Requirements

Every handler logs:
1. Entry with request type and relevant IDs.
2. Exit with duration.
3. Errors with full exception details.

Use the `LoggingBehaviour` MediatR pipeline:

```csharp
// Automatically added to all handlers via DI registration
public class LoggingBehaviour<TRequest, TResponse>(ILogger<LoggingBehaviour<TRequest, TResponse>> logger)
    : IPipelineBehavior<TRequest, TResponse>
{
    public async Task<TResponse> Handle(TRequest request, RequestHandlerDelegate<TResponse> next, CancellationToken ct)
    {
        var requestName = typeof(TRequest).Name;
        logger.LogInformation("Handling {RequestName} {@Request}", requestName, request);
        var sw = Stopwatch.StartNew();
        try {
            return await next();
        }
        finally {
            logger.LogInformation("Handled {RequestName} in {ElapsedMs}ms", requestName, sw.ElapsedMilliseconds);
        }
    }
}
```

---

## What NOT to Do

- Do not put business logic in controllers — controllers only validate auth and call MediatR.
- Do not use `var` for non-obvious types.
- Do not use `async void` methods.
- Do not use `Task.Result` or `.GetAwaiter().GetResult()` — always `await`.
- Do not use `.Result` to access task results synchronously.
- Do not write raw SQL unless absolutely necessary (use EF Core; raw SQL in comments + EF fallback).
- Do not catch generic `Exception` — catch specific exception types.
- Do not return `null` from queries — throw `NotFoundException` or return empty collections.

---

*Phase 02 Instructions — AI Portal — v1.0*
