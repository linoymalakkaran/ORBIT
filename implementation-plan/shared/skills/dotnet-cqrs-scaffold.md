# Skill: .NET CQRS Scaffold

## Skill ID
`dotnet-cqrs-scaffold`

## Description
Generates a complete .NET 9 CQRS microservice solution following AD Ports conventions. Use this skill to scaffold a new backend service for any bounded context.

## When To Use
- Creating a new backend microservice for an AD Ports project.
- Adding a new bounded context to an existing service.
- Scaffolding CQRS handlers from an OpenAPI stub.

---

## Inputs Required

```json
{
  "serviceName": "string — PascalCase, e.g. DgdDeclarationService",
  "namespace": "string — Kubernetes namespace, e.g. dgd-prod",
  "boundedContexts": [
    {
      "name": "string — PascalCase",
      "entities": ["string"],
      "commands": ["CreateX", "UpdateX", "DeleteX"],
      "queries": ["GetXById", "ListX"]
    }
  ],
  "integrations": {
    "keycloak": true,
    "mdm": false,
    "notification": true,
    "audit": true,
    "rabbitMq": false,
    "camunda": false
  },
  "database": {
    "schema": "string — snake_case schema name",
    "rlsEnabled": true
  }
}
```

---

## Output Structure

```
{ServiceName}/
├── src/
│   ├── {ServiceName}.Api/            — Program.cs, Controllers, Middleware
│   ├── {ServiceName}.Application/    — Commands, Queries, Behaviours
│   ├── {ServiceName}.Domain/         — Entities, Events, ValueObjects
│   └── {ServiceName}.Infrastructure/ — DbContext, Migrations, ExternalClients
├── tests/
│   ├── {ServiceName}.UnitTests/
│   └── {ServiceName}.IntegrationTests/
├── helm/{service-name}/              — Helm chart
└── Dockerfile
```

---

## Key Patterns Generated

### Program.cs Registration

```csharp
// Auto-generated registration includes:
builder.Services.AddMediatR(cfg => cfg.RegisterServicesFromAssembly(Assembly.GetExecutingAssembly()));
builder.Services.AddFluentValidationAutoValidation();
builder.Services.AddDbContext<{ServiceName}DbContext>(opt => opt.UseNpgsql(config.GetConnectionString("Postgres")));
builder.Services.AddAuthentication(JwtBearerDefaults.AuthenticationScheme).AddJwtBearer(...);
builder.Services.AddOpenTelemetry()...;
builder.Services.AddHealthChecks().AddNpgSql(...).AddUrlGroup(new Uri(config["Keycloak:Authority"]), "keycloak");
```

### MediatR Pipeline Behaviours

All three AD Ports behaviours are registered:
1. `ValidationBehaviour<TRequest, TResponse>` — FluentValidation.
2. `LoggingBehaviour<TRequest, TResponse>` — Structured logging with request/response.
3. `LedgerEventBehaviour<TRequest, TResponse>` — Pipeline Ledger recording.

### CQRS Handler Template

Follows the pattern in `shared/instructions/coding-standards-csharp.md`:
- `IRequestHandler<TCommand, Result<TId>>`
- Constructor injection only.
- `CancellationToken` in every async method.
- `AsNoTracking()` on all read queries.
- Result pattern for domain errors (no exceptions for business rules).

---

## Usage Example

Prompt to AI agent:
```
Using the dotnet-cqrs-scaffold skill, generate the DGD Declaration Service.
Bounded context: Declaration with entities [Declaration, CargoManifest].
Commands: [CreateDeclaration, SubmitDeclaration, ApproveDeclaration].
Queries: [GetDeclarationById, ListDeclarationsByShipper].
Integrations: Keycloak=true, Notification=true, RabbitMq=true.
DB schema: dgd, RLS enabled.
```

---

## Acceptance Criteria

- [ ] `dotnet build` passes with zero warnings.
- [ ] `dotnet test` passes all unit and integration tests.
- [ ] SonarQube quality gate passes.
- [ ] Dockerfile builds and container starts.
- [ ] Helm chart deploys to dev AKS (`helm install --dry-run` clean).
- [ ] `/health/live` and `/health/ready` return 200.

---

## References

- [shared/instructions/coding-standards-csharp.md](../instructions/coding-standards-csharp.md)
- [Phase 12 — Backend Specialist Agent](../../phases/phase-12/phase-12.md)
- [Phase 02 — Core Data Layer](../../phases/phase-02/phase-02.md)

---

*shared/skills/dotnet-cqrs-scaffold.md — AI Portal — v1.0*
