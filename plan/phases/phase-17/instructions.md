# Instructions — Phase 17: Observability & Monitoring

> Add this file to your IDE's custom instructions when setting up observability for AD Ports AI Portal services.

---

## Context

You are setting up **observability** for the AD Ports AI Portal — OpenTelemetry instrumentation, Azure Monitor integration, Grafana dashboards, PagerDuty alerting, and SLO tracking. Every generated service must export traces, metrics, and structured logs using the OpenTelemetry standard.

---

## OpenTelemetry Configuration (.NET)

```csharp
// Program.cs — REQUIRED OTEL setup for every .NET service
builder.Services.AddOpenTelemetry()
    .WithTracing(tracing =>
        tracing
            .SetResourceBuilder(ResourceBuilder.CreateDefault()
                .AddService(builder.Configuration["ServiceName"]!)
                .AddAttributes(new Dictionary<string, object>
                {
                    ["deployment.environment"] = builder.Configuration["ASPNETCORE_ENVIRONMENT"]!,
                    ["adports.domain"]         = builder.Configuration["Domain"]!,
                    ["adports.version"]        = Assembly.GetExecutingAssembly().GetName().Version!.ToString(),
                }))
            .AddAspNetCoreInstrumentation()
            .AddHttpClientInstrumentation()
            .AddEntityFrameworkCoreInstrumentation()
            .AddOtlpExporter(o => o.Endpoint = new Uri(builder.Configuration["Otel:Endpoint"]!)))
    .WithMetrics(metrics =>
        metrics
            .AddAspNetCoreInstrumentation()
            .AddHttpClientInstrumentation()
            .AddRuntimeInstrumentation()
            .AddOtlpExporter(o => o.Endpoint = new Uri(builder.Configuration["Otel:Endpoint"]!)));

// Structured logging — Serilog with OTEL sink
builder.Host.UseSerilog((ctx, cfg) =>
    cfg.ReadFrom.Configuration(ctx.Configuration)
       .Enrich.WithSpanId()
       .Enrich.WithTraceId()
       .Enrich.WithProperty("service", ctx.Configuration["ServiceName"])
       .WriteTo.OpenTelemetry());
```

## Mandatory Custom Metrics

Every service must emit these custom metrics:

```csharp
// Define in a dedicated Metrics.cs file per service
public static class DeclarationsMetrics
{
    private static readonly Meter Meter = new("AdPorts.Declarations", "1.0");

    public static readonly Counter<long> DeclarationsSubmitted =
        Meter.CreateCounter<long>("declarations.submitted.total",
            description: "Total declarations submitted");

    public static readonly Histogram<double> ProcessingDuration =
        Meter.CreateHistogram<double>("declarations.processing.duration.ms",
            unit: "ms",
            description: "Declaration processing duration");

    public static readonly UpDownCounter<long> ActiveDeclarations =
        Meter.CreateUpDownCounter<long>("declarations.active.count",
            description: "Currently active declarations");
}

// Usage in handler:
DeclarationsMetrics.DeclarationsSubmitted.Add(1,
    new("cargo_type", declaration.CargoType),
    new("origin_port", declaration.OriginPort));
```

## SLO Targets

| Service | SLO | Alert Threshold |
|---------|-----|-----------------|
| Portal UI | 99.5% availability | < 99.0% triggers P2 |
| Orchestrator API | 99.9% availability, P95 < 500ms | P95 > 800ms triggers P2 |
| MCP Servers | 99.5% availability, P99 < 2s | P99 > 3s triggers P3 |
| Hook Engine | 99.99% availability, P99 < 20ms | P99 > 30ms triggers P1 |
| Pipeline Ledger | 99.99% availability | Any unavailability triggers P1 |
| LLM Gateway | 99.0% availability, P95 < 30s | P95 > 60s triggers P2 |

## Grafana Dashboard Requirements

Every service must have a Grafana dashboard with:
- **Golden Signals panel**: Request rate, error rate, latency (P50/P95/P99), saturation
- **Business metrics panel**: Domain-specific counters (e.g. declarations submitted/hour)
- **LLM Cost panel** (Orchestrator only): Cost per project, per tier, per day
- **Dependency health panel**: DB, Redis, external API status

```
Dashboard naming: "AI Portal — {Service Name}"
Folder: "AI Portal Services"
Tags: ["ai-portal", "{domain}", "{environment}"]
```

## Forbidden Patterns

| Pattern | Reason |
|---------|--------|
| `Console.WriteLine` for logging | Use `ILogger<T>` — console logs lose context |
| Logging passwords, tokens, PII | Serilog destructuring must exclude sensitive fields |
| Creating dashboards manually in Grafana UI | Use Grafana-as-code (JSON provisioning) |
| PagerDuty alert without runbook link | Every alert must link to a runbook in the Fabric |
| Using `Thread.Sleep` / `Task.Delay` in health checks | Health checks must be non-blocking |

---

*Instructions — Phase 17 — AD Ports AI Portal — Applies to: Platform Squad*
