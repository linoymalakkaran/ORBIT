# Phase 14 — Database & Integration Agents

## Summary

Implement the **Database Agent** (PostgreSQL migration generation, RLS policies, performance index recommendations) and the **Integration Agent** (RabbitMQ with MassTransit, Camunda BPMN workflow generation, Saga pattern, inbox/outbox). These agents handle the data persistence and messaging layers of generated services.

---

## Objectives

1. Implement Database Agent — schema migration generator (EF Core + DbUp).
2. Implement Database Agent — RLS policy generator from OpenFGA model.
3. Implement Database Agent — index recommendation engine.
4. Implement Database Agent — data seeding generator (dev + staging).
5. Implement Integration Agent — RabbitMQ exchange/queue topology generator.
6. Implement Integration Agent — MassTransit consumer generator.
7. Implement Integration Agent — Saga definition generator.
8. Implement Integration Agent — Camunda BPMN generator for complex workflows.
9. Implement Integration Agent — inbox/outbox pattern scaffold.
10. Wire both agents to Orchestrator delegation framework.

---

## Prerequisites

- Phase 10 (Orchestrator).
- Phase 12 (Backend Specialist Agent — generates DbContext scaffolds).
- Phase 02 (Core Data Layer — shared Postgres cluster).
- Phase 01 (Strimzi Kafka — alternative for event streaming).

---

## Duration

**3 weeks** (runs after Phase 12 foundation is stable)

**Squad:** Delivery Agents Squad (1 senior .NET + 1 Python/AI + 1 DBA-skilled engineer)

---

## Deliverables

| # | Deliverable | Acceptance Criterion |
|---|------------|---------------------|
| D1 | EF Core migration generator | Migrations generated and `dotnet ef database update` succeeds |
| D2 | DbUp script generator | SQL scripts ordered and applied correctly on clean Postgres |
| D3 | RLS policy generator | Row-level security filters by user_id/tenant_id from Keycloak claim |
| D4 | Index recommendations | Recommendations documented; critical indexes generated as migrations |
| D5 | Data seeding generator | Dev seed data applied via `dotnet ef database update` |
| D6 | RabbitMQ topology generator | Exchanges + queues declared; messages routable |
| D7 | MassTransit consumer generator | Consumer class + IConsumer<TMessage> implementation generated |
| D8 | Saga generator | Saga state machine with compensating transactions |
| D9 | Camunda BPMN generator | Valid .bpmn XML deployed to Camunda; process starts correctly |
| D10 | Inbox/outbox scaffold | Outbox table + publisher; inbox table + deduplication |

---

## Database Agent

### EF Core Migration Generator

The Database Agent examines the component decomposition and generates EF Core entity configurations and migrations:

```csharp
// Generated: {Entity}Configuration.cs
public class DeclarationConfiguration : IEntityTypeConfiguration<Declaration>
{
    public void Configure(EntityTypeBuilder<Declaration> builder)
    {
        builder.ToTable("declarations", "dgd");
        builder.HasKey(d => d.Id);
        builder.Property(d => d.Id).HasColumnName("id");
        builder.Property(d => d.CargoType)
            .HasColumnName("cargo_type")
            .HasConversion<string>()
            .IsRequired();
        builder.Property(d => d.Weight)
            .HasColumnName("weight")
            .HasColumnType("decimal(18,4)")
            .IsRequired();
        builder.Property(d => d.Status)
            .HasColumnName("status")
            .HasConversion<string>()
            .IsRequired()
            .HasDefaultValue(DeclarationStatus.Draft);

        // Audit columns on every entity
        builder.Property(d => d.CreatedAt).HasColumnName("created_at").HasDefaultValueSql("now()");
        builder.Property(d => d.CreatedBy).HasColumnName("created_by").IsRequired();
        builder.Property(d => d.UpdatedAt).HasColumnName("updated_at");
        builder.Property(d => d.UpdatedBy).HasColumnName("updated_by");
        builder.Property(d => d.RowVersion)
            .HasColumnName("row_version")
            .IsRowVersion()
            .IsConcurrencyToken();

        // Row-level security support
        builder.HasAnnotation("adports:rls-enabled", true);
        builder.HasAnnotation("adports:rls-column", "tenant_id");
    }
}
```

### RLS Policy Generator

```sql
-- Generated RLS policy for declarations table
ALTER TABLE dgd.declarations ENABLE ROW LEVEL SECURITY;
ALTER TABLE dgd.declarations FORCE ROW LEVEL SECURITY;

-- Policy: users can only see declarations in their tenant
CREATE POLICY declarations_tenant_isolation
  ON dgd.declarations
  FOR ALL
  USING (tenant_id = current_setting('app.current_tenant_id', true)::uuid)
  WITH CHECK (tenant_id = current_setting('app.current_tenant_id', true)::uuid);

-- Policy: service accounts bypass RLS
CREATE POLICY declarations_service_bypass
  ON dgd.declarations
  FOR ALL
  TO dgd_service_role
  USING (true);
```

The .NET infrastructure layer sets `app.current_tenant_id` from the JWT on each request:

```csharp
// Generated: TenantRlsInterceptor.cs
public class TenantRlsInterceptor : DbCommandInterceptor
{
    public override async ValueTask<InterceptionResult<DbDataReader>> ReaderExecutingAsync(
        DbCommand command, CommandEventData eventData, InterceptionResult<DbDataReader> result, CancellationToken cancellationToken = default)
    {
        await SetTenantContextAsync(command.Connection!, _httpContextAccessor.HttpContext?.GetTenantId());
        return result;
    }

    private static async Task SetTenantContextAsync(DbConnection connection, string? tenantId)
    {
        await using var cmd = connection.CreateCommand();
        cmd.CommandText = $"SET LOCAL app.current_tenant_id = '{tenantId ?? string.Empty}';";
        await cmd.ExecuteNonQueryAsync();
    }
}
```

---

## Integration Agent

### MassTransit Consumer Generator

Given a domain event `DeclarationSubmitted`, the Integration Agent generates:

```csharp
// Generated: DeclarationSubmittedConsumer.cs
public class DeclarationSubmittedConsumer : IConsumer<DeclarationSubmitted>
{
    private readonly ISender _mediator;
    private readonly ILogger<DeclarationSubmittedConsumer> _logger;

    public DeclarationSubmittedConsumer(ISender mediator, ILogger<DeclarationSubmittedConsumer> logger)
    {
        _mediator = mediator;
        _logger = logger;
    }

    public async Task Consume(ConsumeContext<DeclarationSubmitted> context)
    {
        _logger.LogInformation("Processing DeclarationSubmitted for {DeclarationId}", context.Message.DeclarationId);
        await _mediator.Send(new ProcessSubmittedDeclarationCommand(context.Message.DeclarationId));
    }
}

// Generated: consumer registration in DependencyInjection.cs
services.AddMassTransit(x =>
{
    x.AddConsumer<DeclarationSubmittedConsumer>()
        .Endpoint(e => { e.Name = "dgd-declaration-submitted"; e.PrefetchCount = 10; });

    x.UsingRabbitMq((ctx, cfg) =>
    {
        cfg.Host(config["RabbitMq:Host"], config["RabbitMq:VirtualHost"], h =>
        {
            h.Username(config["RabbitMq:Username"]);
            h.Password(config["RabbitMq:Password"]);
        });
        cfg.UseMessageRetry(r => r.Exponential(3, TimeSpan.FromSeconds(1), TimeSpan.FromSeconds(10), TimeSpan.FromSeconds(3)));
        cfg.ConfigureEndpoints(ctx);
    });
});
```

### Saga Generator

For a multi-step Declaration process (submit → validate customs → calculate fees → notify):

```csharp
// Generated: DeclarationProcessSaga.cs
public class DeclarationProcessSaga : MassTransitStateMachine<DeclarationProcessSagaState>
{
    public State Submitted { get; private set; } = null!;
    public State AwaitingCustomsValidation { get; private set; } = null!;
    public State AwaitingFeeCalculation { get; private set; } = null!;
    public State Completed { get; private set; } = null!;
    public State Failed { get; private set; } = null!;

    public Event<DeclarationSubmitted> DeclarationSubmittedEvent { get; private set; } = null!;
    public Event<CustomsValidationCompleted> CustomsValidationCompletedEvent { get; private set; } = null!;
    public Event<FeesCalculated> FeesCalculatedEvent { get; private set; } = null!;

    public DeclarationProcessSaga()
    {
        InstanceState(s => s.CurrentState);
        Event(() => DeclarationSubmittedEvent, e => e.CorrelateById(c => c.Message.DeclarationId));
        Event(() => CustomsValidationCompletedEvent, e => e.CorrelateById(c => c.Message.DeclarationId));
        Event(() => FeesCalculatedEvent, e => e.CorrelateById(c => c.Message.DeclarationId));

        Initially(
            When(DeclarationSubmittedEvent)
                .TransitionTo(AwaitingCustomsValidation)
                .Publish(ctx => new ValidateCustomsDeclarationCommand(ctx.Message.DeclarationId))
        );

        During(AwaitingCustomsValidation,
            When(CustomsValidationCompletedEvent)
                .TransitionTo(AwaitingFeeCalculation)
                .Publish(ctx => new CalculateFeesCommand(ctx.Message.DeclarationId))
        );

        During(AwaitingFeeCalculation,
            When(FeesCalculatedEvent)
                .TransitionTo(Completed)
                .Publish(ctx => new SendDeclarationNotificationCommand(ctx.Message.DeclarationId))
        );
    }
}
```

### Camunda BPMN Generator

For a SINTECE customs integration that requires a wait-for-callback pattern:

```xml
<!-- Generated: dgd-customs-declaration.bpmn -->
<?xml version="1.0" encoding="UTF-8"?>
<definitions xmlns="http://www.omg.org/spec/BPMN/20100524/MODEL" ...>
  <process id="DgdCustomsDeclaration" name="DGD Customs Declaration" isExecutable="true">

    <startEvent id="StartEvent_DeclarationSubmitted">
      <outgoing>Flow_to_ValidateData</outgoing>
    </startEvent>

    <serviceTask id="Task_ValidateData" name="Validate Declaration Data"
      camunda:type="external" camunda:topic="adports-validate-declaration">
      <incoming>Flow_to_ValidateData</incoming>
      <outgoing>Flow_to_SendToSINTECE</outgoing>
    </serviceTask>

    <serviceTask id="Task_SendToSINTECE" name="Send to SINTECE"
      camunda:type="external" camunda:topic="adports-sintece-submit">
      <incoming>Flow_to_SendToSINTECE</incoming>
      <outgoing>Flow_to_WaitResponse</outgoing>
    </serviceTask>

    <!-- Wait for async SINTECE callback (up to 2 business days) -->
    <receiveTask id="Task_WaitSINTECEResponse" name="Wait SINTECE Response"
      messageRef="Message_SINTECEResponse">
      <incoming>Flow_to_WaitResponse</incoming>
      <outgoing>Flow_to_ProcessResponse</outgoing>
    </receiveTask>

    <!-- ... remaining tasks ... -->
  </process>
</definitions>
```

---

## Inbox/Outbox Pattern

Every generated service that publishes events gets the transactional outbox pattern:

```sql
-- Generated migration: add outbox table
CREATE TABLE {schema}.outbox_messages (
    id          uuid        PRIMARY KEY DEFAULT gen_random_uuid(),
    type        text        NOT NULL,
    payload     jsonb       NOT NULL,
    created_at  timestamptz NOT NULL DEFAULT now(),
    processed_at timestamptz,
    error       text
);

CREATE INDEX idx_outbox_unprocessed ON {schema}.outbox_messages (created_at)
    WHERE processed_at IS NULL;
```

---

## Step-by-Step Execution Plan

### Week 1: Database Agent

- [ ] Implement EF Core entity configuration generator.
- [ ] Implement migration generator (adds to `Infrastructure/Persistence/Migrations/`).
- [ ] Implement RLS policy SQL generator + Tenant interceptor.
- [ ] Implement index recommendation engine (read EXPLAIN ANALYZE output → suggest indexes).
- [ ] Test: DGD declarations schema generated and applied to Postgres.

### Week 2: Integration Agent

- [ ] Implement RabbitMQ exchange/queue topology generator.
- [ ] Implement MassTransit consumer generator from domain events.
- [ ] Implement inbox/outbox scaffold generator.
- [ ] Implement Saga state machine generator.
- [ ] Test: Producer → consumer round-trip with DGD events.

### Week 3: Camunda + Agent Wiring

- [ ] Implement Camunda BPMN generator for complex workflows (> 3 steps with external calls).
- [ ] Implement Camunda worker registration generator.
- [ ] Implement `DatabaseAgentWorker` + `IntegrationAgentWorker` in Orchestrator framework.
- [ ] Integration test: Backend Agent generates DbContext → Database Agent adds migrations → Integration Agent wires consumers; all pass.

---

## Gate Criterion

- DGD service schema migrated to Postgres with RLS policies active.
- RabbitMQ topology created; `DeclarationSubmitted` event flows from publisher to consumer.
- Saga processes DGD declaration through all states (Submitted → Validated → Fees Calculated → Notified).
- Camunda BPMN process starts for SINTECE integration; wait state reached.
- Inbox/outbox relay publishes pending outbox messages.

---

*Phase 14 — Database & Integration Agents — AI Portal — v1.0*
