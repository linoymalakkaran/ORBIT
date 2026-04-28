# AD Ports C# Coding Standards

## Applies To

All .NET 9 microservices generated or maintained by the AI Portal. Applies to: Backend Specialist Agent, Ticket Implementation Agent, PR Review Agent. Load this file as custom instructions in Copilot / Cursor for any C# project.

---

## Solution Architecture

Every service follows Clean Architecture with CQRS:

```
{ServiceName}.Api          → Controllers, Middleware, DI composition root
{ServiceName}.Application  → Commands, Queries, Handlers, Validators, DTOs, Behaviours
{ServiceName}.Domain       → Entities, Events, Value Objects, Enums (no framework references)
{ServiceName}.Infrastructure → DbContext, Migrations, ExternalService clients, Messaging
{ServiceName}.UnitTests
{ServiceName}.IntegrationTests
```

**Rule:** Domain layer must have zero external package references (no EF Core, no MediatR).

---

## CQRS Naming Conventions

| Type | Pattern | Example |
|------|---------|---------|
| Command | `{Verb}{Entity}Command` | `CreateDeclarationCommand` |
| Command Handler | `{Verb}{Entity}CommandHandler` | `CreateDeclarationCommandHandler` |
| Command Validator | `{Verb}{Entity}CommandValidator` | `CreateDeclarationCommandValidator` |
| Query | `Get{Entity}{Qualifier}Query` | `GetDeclarationByIdQuery` |
| Query Handler | `Get{Entity}{Qualifier}QueryHandler` | `GetDeclarationByIdQueryHandler` |
| Result DTO | `{Entity}Dto` or `{Entity}Response` | `DeclarationDto` |
| Domain Event | `{Entity}{PastTense}Event` | `DeclarationSubmittedEvent` |

---

## MediatR Handler Pattern

```csharp
// REQUIRED pattern for all command handlers
public class CreateDeclarationCommandHandler
    : IRequestHandler<CreateDeclarationCommand, Result<Guid>>
{
    private readonly IDeclarationDbContext _context;
    private readonly ILogger<CreateDeclarationCommandHandler> _logger;

    // Constructor injection ONLY — no service locator
    public CreateDeclarationCommandHandler(
        IDeclarationDbContext context,
        ILogger<CreateDeclarationCommandHandler> logger)
    {
        _context = context;
        _logger = logger;
    }

    public async Task<Result<Guid>> Handle(
        CreateDeclarationCommand request,
        CancellationToken cancellationToken)
    {
        // 1. Create domain entity
        var declaration = Declaration.Create(
            request.CargoType,
            request.Weight,
            request.OriginPort,
            request.DestinationPort);

        // 2. Persist
        _context.Declarations.Add(declaration);
        await _context.SaveChangesAsync(cancellationToken);

        // 3. Structured log (no string interpolation in log messages)
        _logger.LogInformation(
            "Declaration {DeclarationId} created by {UserId}",
            declaration.Id,
            request.CurrentUserId);

        return Result.Success(declaration.Id);
    }
}
```

---

## FluentValidation Pattern

```csharp
public class CreateDeclarationCommandValidator
    : AbstractValidator<CreateDeclarationCommand>
{
    public CreateDeclarationCommandValidator()
    {
        RuleFor(x => x.CargoType)
            .IsInEnum()
            .WithMessage("CargoType must be a valid enum value.");

        RuleFor(x => x.Weight)
            .GreaterThan(0)
            .LessThanOrEqualTo(999999)
            .WithMessage("Weight must be between 0.01 and 999,999 kg.");

        RuleFor(x => x.OriginPort)
            .NotEmpty()
            .Length(4, 10)
            .Matches(@"^[A-Z]{2}\w{2,8}$")
            .WithMessage("OriginPort must be a valid port code (e.g. AEJEA).");

        // Rule: conditional validation
        When(x => x.CargoType == CargoType.Dangerous, () =>
        {
            RuleFor(x => x.ImoDangerousGoods).NotNull()
                .WithMessage("IMO dangerous goods info required for dangerous cargo.");
            RuleFor(x => x.ImoDangerousGoods!.UnNumber)
                .Matches(@"^\d{4}$")
                .WithMessage("UN number must be exactly 4 digits.");
        });
    }
}
```

---

## EF Core Rules

```csharp
// ALWAYS use AsNoTracking() for read-only queries
var declarations = await _context.Declarations
    .AsNoTracking()
    .Where(d => d.ProjectId == projectId && d.Status != DeclarationStatus.Retired)
    .OrderByDescending(d => d.CreatedAt)
    .Select(d => new DeclarationDto { Id = d.Id, Status = d.Status, ... })
    .ToListAsync(cancellationToken);

// NEVER use .Result or .Wait()
// BAD:  var result = _context.SaveChangesAsync().Result;
// GOOD: var result = await _context.SaveChangesAsync(cancellationToken);

// ALWAYS pass CancellationToken to all async EF operations
await _context.SaveChangesAsync(cancellationToken);

// ALWAYS use snake_case for column names
builder.Property(d => d.CargoType).HasColumnName("cargo_type");

// ALWAYS use HasDefaultValueSql for audit columns
builder.Property(d => d.CreatedAt).HasColumnName("created_at").HasDefaultValueSql("now()");
```

---

## Async Rules

```csharp
// CORRECT: all async methods take CancellationToken
public async Task<Result<Guid>> Handle(CreateDeclarationCommand request, CancellationToken cancellationToken)

// WRONG: async void (swallows exceptions)
// public async void Handle(...) { ... }

// WRONG: blocking on async
// var result = someTask.Result;
// someTask.Wait();

// CORRECT: ConfigureAwait not needed in ASP.NET Core (no SynchronizationContext)
// DO NOT add .ConfigureAwait(false) — it is unnecessary noise in ASP.NET Core
```

---

## Error Handling

All handlers return `Result<T>` (never throw for business rule violations):

```csharp
// Domain method returns Result
public static Result<Declaration> Create(CargoType type, decimal weight, ...)
{
    if (weight <= 0)
        return Result.Failure<Declaration>("Weight must be positive.");
    // ...
    return Result.Success(new Declaration(...));
}

// Controller maps Result to HTTP
[HttpPost]
public async Task<IActionResult> Create([FromBody] CreateDeclarationRequest request)
{
    var result = await _mediator.Send(request.ToCommand(CurrentUserId));
    return result.IsSuccess
        ? CreatedAtAction(nameof(GetById), new { id = result.Value }, result.Value)
        : BadRequest(new { error = result.Error });
}
```

Exception middleware handles unexpected exceptions (returns 500 with correlation ID).

---

## Security Rules

```csharp
// NEVER hardcode secrets
// BAD:  var connStr = "Host=prod-db;Password=S3cret";
// GOOD: var connStr = _config["ConnectionStrings:Postgres"];  // from Vault Agent Injector

// ALWAYS validate JWT claims from Keycloak
var userId = User.FindFirstValue(ClaimTypes.NameIdentifier)
    ?? throw new UnauthorizedException("Missing user claim.");

// ALWAYS use parameterized queries (no string SQL)
// BAD:  _context.Database.ExecuteSqlRaw($"DELETE FROM declarations WHERE id = '{id}'");
// GOOD: _context.Database.ExecuteSqlInterpolated($"DELETE FROM declarations WHERE id = {id}");

// NEVER log sensitive data
// BAD:  _logger.LogInformation("Processing card {CardNumber}", request.CardNumber);
// GOOD: _logger.LogInformation("Processing payment for order {OrderId}", request.OrderId);
```

---

## Observability Requirements

Every service must emit:

```csharp
// Structured logs (Serilog/Microsoft.Extensions.Logging)
_logger.LogInformation(
    "Declaration {DeclarationId} transitioned to {NewStatus} by {UserId}",
    declaration.Id, newStatus, currentUserId);

// Custom metrics (OpenTelemetry)
_declarationsProcessed.Add(1, new TagList { { "cargo_type", request.CargoType.ToString() } });

// Trace spans for external calls
using var span = _tracer.StartActiveSpan("sintece.submit");
span.SetAttribute("declaration.id", declarationId.ToString());
```

---

## Testing Rules

```csharp
// Unit tests: pure domain logic, no I/O
[Fact]
public void Declaration_Create_WithDangerousCargoAndNoIMO_ShouldFail()
{
    var result = Declaration.Create(CargoType.Dangerous, 500, "AEJEA", "AEFJR", imoInfo: null);
    Assert.False(result.IsSuccess);
    Assert.Contains("IMO", result.Error);
}

// Integration tests: real Postgres + RabbitMQ via Testcontainers
// Use CustomWebApplicationFactory<Program> from the generated test fixture
// NEVER mock DbContext in integration tests

// Naming convention: {Method}_{StateUnderTest}_{ExpectedBehavior}
// CreateDeclaration_WithValidRequest_ShouldReturnCreatedWithReferenceNumber
```

---

## Forbidden Patterns

- ❌ `async void` (use `async Task`)
- ❌ `.Result` or `.Wait()` on tasks
- ❌ Hardcoded secrets, passwords, connection strings
- ❌ String SQL queries (use LINQ or interpolated SQL)
- ❌ `new DbContext(...)` directly (use DI)
- ❌ Static state / singletons with mutable state
- ❌ Catching `Exception` base class without rethrowing
- ❌ `.ConfigureAwait(false)` in ASP.NET Core (noise)
- ❌ Magic strings for configuration keys (use constants)
- ❌ Logging sensitive data (card numbers, passwords, tokens)

---

*shared/instructions/coding-standards-csharp.md — AI Portal — v1.0*
