# Phase 12 — Backend Specialist Agent

## Summary

Implement the **Backend Specialist Agent** — the component that generates production-ready .NET 9 CQRS microservices following AD Ports conventions. Given a work package from the Orchestration Agent, the Backend Agent scaffolds a complete .NET solution that passes `dotnet build`, `dotnet test`, SonarQube quality gate, and Checkmarx SAST on first run.

---

## Objectives

1. Implement the .NET CQRS solution template engine (generates full solution structure).
2. Implement domain entity generation from component decomposition.
3. Implement CQRS handler generation (commands + queries from OpenAPI stubs).
4. Implement EF Core DbContext and migration generation.
5. Implement integration wiring (Keycloak, MDM, Notification Hub, Audit Service).
6. Implement Dockerfile + Helm chart generation.
7. Implement OpenTelemetry instrumentation generation.
8. Implement health check generation.
9. Implement unit test scaffold generation (xUnit + Testcontainers).
10. Wire Backend Agent to the Orchestrator delegation framework and Pipeline Ledger.

---

## Prerequisites

- Phase 10 (Orchestrator delegation framework).
- Phase 07 (Capability Fabric — `dotnet-cqrs-scaffold` skill).
- Phase 09 (GitLab MCP — to create repo and push code).
- Phase 08 (Keycloak MCP — to configure service client).

---

## Duration

**3 weeks**

**Squad:** Delivery Agents Squad (2 senior .NET engineers + 1 Python/AI engineer)

---

## Deliverables

| # | Deliverable | Acceptance Criterion |
|---|------------|---------------------|
| D1 | .NET solution generator | `dotnet build` passes on generated solution |
| D2 | Domain entity generation | Entities match component decomposition spec |
| D3 | CQRS handler generation | All commands/queries from OpenAPI stubs implemented as stubs |
| D4 | EF Core + migrations | `dotnet ef database update` applies migrations to Postgres |
| D5 | Shared service wiring | Keycloak auth, MDM client, Notification client all referenced |
| D6 | Dockerfile + Helm chart | Docker image builds; Helm chart deploys to dev AKS |
| D7 | OpenTelemetry | Traces visible in Grafana Tempo for a request through the service |
| D8 | Health checks | `/health/live` + `/health/ready` return correct status |
| D9 | Unit test scaffold | `dotnet test` passes; Testcontainers Postgres + RabbitMQ available |
| D10 | Ledger integration | Agent start + completion events in Pipeline Ledger |

---

## Generated Solution Structure

```
{ServiceName}/
├── src/
│   ├── {ServiceName}.Api/
│   │   ├── Program.cs
│   │   ├── appsettings.json
│   │   ├── appsettings.{env}.json
│   │   ├── Controllers/
│   │   │   ├── HealthController.cs
│   │   │   └── {Resource}Controller.cs       ← one per resource
│   │   ├── Middleware/
│   │   │   ├── ExceptionHandlingMiddleware.cs
│   │   │   └── TelemetryMiddleware.cs
│   │   └── Extensions/
│   │       └── ServiceCollectionExtensions.cs
│   │
│   ├── {ServiceName}.Application/
│   │   ├── Common/
│   │   │   ├── Interfaces/
│   │   │   │   ├── I{ServiceName}DbContext.cs
│   │   │   │   ├── INotificationService.cs
│   │   │   │   └── IAuditService.cs
│   │   │   ├── Behaviours/
│   │   │   │   ├── ValidationBehaviour.cs
│   │   │   │   ├── LoggingBehaviour.cs
│   │   │   │   └── PerformanceBehaviour.cs
│   │   │   └── Exceptions/
│   │   ├── {BoundedContext}/
│   │   │   ├── Commands/
│   │   │   │   └── Create{Entity}/
│   │   │   │       ├── Create{Entity}Command.cs
│   │   │   │       ├── Create{Entity}CommandHandler.cs
│   │   │   │       └── Create{Entity}CommandValidator.cs
│   │   │   └── Queries/
│   │   │       └── Get{Entity}ById/
│   │   │           ├── Get{Entity}ByIdQuery.cs
│   │   │           └── Get{Entity}ByIdQueryHandler.cs
│   │   └── DependencyInjection.cs
│   │
│   ├── {ServiceName}.Domain/
│   │   ├── Entities/
│   │   │   └── {Entity}.cs
│   │   ├── Events/
│   │   │   └── {Entity}CreatedEvent.cs
│   │   ├── ValueObjects/
│   │   └── Enums/
│   │
│   └── {ServiceName}.Infrastructure/
│       ├── Persistence/
│       │   ├── {ServiceName}DbContext.cs
│       │   ├── Migrations/
│       │   └── Configurations/
│       │       └── {Entity}Configuration.cs
│       ├── Identity/
│       │   └── KeycloakTokenValidator.cs
│       ├── ExternalServices/
│       │   ├── MdmClient.cs
│       │   ├── NotificationClient.cs
│       │   └── AuditClient.cs
│       ├── Messaging/
│       │   └── EventPublisher.cs
│       └── DependencyInjection.cs
│
├── tests/
│   ├── {ServiceName}.UnitTests/
│   │   ├── Application/
│   │   └── Domain/
│   └── {ServiceName}.IntegrationTests/
│       ├── {Resource}Tests.cs
│       └── CustomWebApplicationFactory.cs
│
├── Dockerfile
├── {ServiceName}.sln
└── helm/
    └── {service-name}/
        ├── Chart.yaml
        ├── values.yaml
        ├── values-dev.yaml
        ├── values-staging.yaml
        └── templates/
            ├── deployment.yaml
            ├── service.yaml
            ├── ingress.yaml
            ├── configmap.yaml
            └── hpa.yaml
```

---

## Template Engine Design

The Backend Agent uses a **Scriban template engine** (not LLM generation) for the deterministic 70–80% of code:

```csharp
public class DotNetSolutionGenerator
{
    private readonly ITemplateEngine _templates;

    public async Task<GeneratedSolution> GenerateAsync(BackendWorkPackage workPackage)
    {
        var context = new TemplateContext(workPackage);
        var files = new List<GeneratedFile>();

        // Deterministic template generation
        files.Add(await _templates.RenderAsync("Program.cs.scriban", context));
        files.Add(await _templates.RenderAsync("DbContext.cs.scriban", context));

        foreach (var entity in workPackage.Entities)
        {
            var entityCtx = context.ForEntity(entity);
            files.AddRange(await _templates.RenderAllAsync("entity/*.scriban", entityCtx));
        }

        foreach (var command in workPackage.Commands)
        {
            var cmdCtx = context.ForCommand(command);
            files.AddRange(await _templates.RenderAllAsync("command/*.scriban", cmdCtx));
        }

        // LLM generation for business logic stubs (20-30%)
        foreach (var handler in workPackage.Handlers.Where(h => h.RequiresLogic))
        {
            var logic = await _llmClient.GenerateHandlerLogicAsync(handler, context);
            files.Add(new GeneratedFile(handler.FilePath, logic));
        }

        return new GeneratedSolution(files);
    }
}
```

Key templates (Scriban):
- `Program.cs.scriban` — wires all middleware, CQRS, EF Core, OTEL, Keycloak auth.
- `DbContext.cs.scriban` — EF Core context with all entity configurations.
- `entity/Entity.cs.scriban` — domain entity with value objects.
- `command/Command.cs.scriban` — MediatR command + validator stubs.
- `query/Query.cs.scriban` — MediatR query + handler stubs.
- `controller/ResourceController.cs.scriban` — REST controller mapping HTTP to MediatR.
- `Dockerfile.scriban` — Multi-stage Dockerfile with .NET 9 base images.
- `helm/deployment.yaml.scriban` — AKS deployment with OTEL, Vault, health probes.

---

## Standard Wiring (Every Generated Service Gets)

```csharp
// Program.cs — every generated service includes this
builder.Services
    .AddAuthentication(JwtBearerDefaults.AuthenticationScheme)
    .AddJwtBearer(options => {
        options.Authority = config["Keycloak:Authority"];
        options.Audience = config["Keycloak:ClientId"];
    });

builder.Services.AddDbContext<{ServiceName}DbContext>(options =>
    options.UseNpgsql(
        config["Database:ConnectionString"],
        npgsql => npgsql.EnableRetryOnFailure(3)
    )
);

builder.Services.AddOpenTelemetry()
    .WithTracing(tracing => tracing
        .AddAspNetCoreInstrumentation()
        .AddHttpClientInstrumentation()
        .AddEntityFrameworkCoreInstrumentation()
        .AddOtlpExporter(opts => opts.Endpoint = new Uri(config["Otel:Endpoint"]))
    )
    .WithMetrics(metrics => metrics
        .AddAspNetCoreInstrumentation()
        .AddRuntimeInstrumentation()
        .AddPrometheusExporter()
    );

builder.Services.AddHealthChecks()
    .AddNpgSql(config["Database:ConnectionString"], name: "postgres")
    .AddUrlGroup(new Uri(config["Keycloak:Authority"] + "/health/ready"), name: "keycloak");

// AD Ports shared service clients
builder.Services
    .AddAdPortsMdmClient(config.GetSection("MdmService"))
    .AddAdPortsNotificationClient(config.GetSection("NotificationService"))
    .AddAdPortsAuditClient(config.GetSection("AuditService"));
```

---

## Integration Test Scaffold

```csharp
// CustomWebApplicationFactory.cs — Testcontainers
public class CustomWebApplicationFactory<TProgram> : WebApplicationFactory<TProgram>
    where TProgram : class
{
    private readonly PostgreSqlContainer _postgres = new PostgreSqlBuilder()
        .WithImage("postgres:16")
        .WithDatabase("test_db")
        .Build();

    private readonly RabbitMqContainer _rabbitmq = new RabbitMqBuilder()
        .WithImage("rabbitmq:3.13-management")
        .Build();

    protected override void ConfigureWebHost(IWebHostBuilder builder)
    {
        builder.ConfigureServices(services =>
        {
            // Replace real DbContext with test one
            services.RemoveAll<DbContextOptions<{ServiceName}DbContext>>();
            services.AddDbContext<{ServiceName}DbContext>(options =>
                options.UseNpgsql(_postgres.GetConnectionString()));
        });
    }

    public override async ValueTask DisposeAsync()
    {
        await _postgres.StopAsync();
        await _rabbitmq.StopAsync();
        await base.DisposeAsync();
    }
}
```

---

## Step-by-Step Execution Plan

### Week 1: Core Templates

- [ ] Implement Scriban template engine wrapper.
- [ ] Author `Program.cs.scriban`, `DbContext.cs.scriban`, `Entity.cs.scriban`.
- [ ] Author `Command.cs.scriban` + `CommandHandler.cs.scriban` + `Validator.cs.scriban`.
- [ ] Author `Query.cs.scriban` + `QueryHandler.cs.scriban`.
- [ ] Test: generate DGD declaration service; `dotnet build` passes.

### Week 2: Controllers, Helm, Docker, Tests

- [ ] Author `ResourceController.cs.scriban` (maps HTTP to MediatR).
- [ ] Author `Dockerfile.scriban` (multi-stage, non-root user, health check).
- [ ] Author `helm/` templates (deployment, service, ingress, configmap, HPA).
- [ ] Author `IntegrationTests.cs.scriban` (Testcontainers fixture + happy-path tests).
- [ ] Test: Docker image builds; Helm chart deploys to dev AKS.

### Week 3: Agent Framework + Wiring

- [ ] Implement `BackendAgentWorker` (receives work package from Orchestrator, runs generator, pushes to GitLab, records Ledger).
- [ ] Wire to Phase 10 Orchestrator delegation framework.
- [ ] Integration test: Orchestrator delegates to Backend Agent → repo created in GitLab → `dotnet build` passes in pipeline.
- [ ] Load test: generate 5 services in parallel; all succeed.

---

## Gate Criterion

- Generated solution for the DGD use case passes: `dotnet build` + `dotnet test` + SonarQube quality gate + Checkmarx SAST.
- Generated Dockerfile builds without errors; image runs and `/health/live` returns 200.
- Generated Helm chart deploys to dev AKS.
- GitLab repository created with protected main branch and CI pipeline.
- Pipeline Ledger records agent start, completion, and repo URL as artifact.

---

*Phase 12 — Backend Specialist Agent — AI Portal — v1.0*
