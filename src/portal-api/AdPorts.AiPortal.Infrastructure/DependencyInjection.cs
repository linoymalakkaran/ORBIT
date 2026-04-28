using AdPorts.AiPortal.Application.Common.Interfaces;
using AdPorts.AiPortal.Infrastructure.Identity;
using AdPorts.AiPortal.Infrastructure.Messaging;
using AdPorts.AiPortal.Infrastructure.Persistence;
using Microsoft.EntityFrameworkCore;
using Microsoft.Extensions.Configuration;
using Microsoft.Extensions.DependencyInjection;

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

        return services;
    }
}
