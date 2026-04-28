using DbUp;
using Microsoft.Extensions.Configuration;
using Microsoft.Extensions.Logging;

namespace AdPorts.AiPortal.Infrastructure.Persistence;

public static class DbUpMigrationRunner
{
    public static void Run(IConfiguration config, ILogger logger)
    {
        var connectionString = config.GetConnectionString("Portal")!;

        EnsureDatabase.For.PostgresqlDatabase(connectionString);

        var upgrader = DeployChanges.To
            .PostgresqlDatabase(connectionString)
            .WithScriptsEmbeddedInAssembly(typeof(DbUpMigrationRunner).Assembly)
            .WithTransaction()
            .LogToConsole()
            .Build();

        if (upgrader.IsUpgradeRequired())
        {
            logger.LogInformation("Running DbUp migrations...");
            var result = upgrader.PerformUpgrade();
            if (!result.Successful)
            {
                logger.LogError(result.Error, "DbUp migration failed");
                throw result.Error;
            }
            logger.LogInformation("DbUp migrations complete");
        }
    }
}
