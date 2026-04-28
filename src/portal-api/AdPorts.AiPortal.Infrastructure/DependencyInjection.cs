using AdPorts.AiPortal.Application.Common.Interfaces;
using AdPorts.AiPortal.Application.Context;
using AdPorts.AiPortal.Infrastructure.Identity;
using AdPorts.AiPortal.Infrastructure.Messaging;
using AdPorts.AiPortal.Infrastructure.Persistence;
using AdPorts.AiPortal.Infrastructure.Services;
using Microsoft.EntityFrameworkCore;
using Microsoft.Extensions.Configuration;
using Microsoft.Extensions.DependencyInjection;
using StackExchange.Redis;

namespace AdPorts.AiPortal.Infrastructure;

public static class DependencyInjection
{
    public static IServiceCollection AddInfrastructureServices(
        this IServiceCollection services, IConfiguration config)
    {
        // EF Core — Postgres
        services.AddDbContext<PortalDbContext>(opts =>
            opts.UseNpgsql(config.GetConnectionString("Portal"),
                npg => npg.EnableRetryOnFailure(3))
                .UseSnakeCaseNamingConvention());

        services.AddScoped<IPortalDbContext>(sp => sp.GetRequiredService<PortalDbContext>());

        // Identity / Authorization
        services.AddScoped<ICurrentUser, CurrentUserService>();
        services.AddScoped<IAuthorizationService, OpenFgaAuthorizationService>();

        // Kafka
        services.Configure<KafkaOptions>(config.GetSection("Kafka"));
        services.AddSingleton<IEventPublisher, KafkaEventPublisher>();

        // Redis — Shared Context
        services.AddSingleton<IConnectionMultiplexer>(
            _ => ConnectionMultiplexer.Connect(config.GetConnectionString("Redis") ?? "redis:6379"));
        services.AddScoped<IContextService, RedisContextService>();

        return services;
    }
}
