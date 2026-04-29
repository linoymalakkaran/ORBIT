using System;
using System.Reflection;
using DbUp;
using DbUp.Engine;
using Microsoft.Extensions.Logging;

namespace AdPorts.AiPortal.Infrastructure.Services;

/// <summary>
/// Phase 02 – G03: Runs raw SQL migration scripts embedded in this assembly
/// using DbUp. Call Run() before EF Core migrations on application startup.
/// </summary>
public static class DbUpMigrationRunner
{
    /// <summary>
    /// Applies all pending *.sql scripts from the
    /// AdPorts.AiPortal.Infrastructure.Migrations.DbUp namespace.
    /// Returns true when upgrades succeed; throws on failure.
    /// </summary>
    public static bool Run(string connectionString, ILogger? logger = null)
    {
        ArgumentException.ThrowIfNullOrWhiteSpace(connectionString);

        var upgrader = DeployChanges.To
            .PostgresqlDatabase(connectionString)
            .WithScriptsEmbeddedInAssembly(
                Assembly.GetExecutingAssembly(),
                s => s.Contains("Migrations.DbUp"))
            .WithTransactionPerScript()
            .LogToConsole()
            .Build();

        var result = upgrader.PerformUpgrade();

        if (!result.Successful)
        {
            var ex = result.Error ?? new Exception("DbUp: unknown upgrade failure");
            logger?.LogCritical(ex, "DbUp migration failed on script '{Script}'",
                result.ErrorScript?.Name ?? "<unknown>");
            throw ex;
        }

        if (result.Scripts.Count > 0)
        {
            logger?.LogInformation(
                "DbUp applied {Count} migration(s): {Scripts}",
                result.Scripts.Count,
                string.Join(", ", System.Linq.Enumerable.Select(result.Scripts, s => s.Name)));
        }
        else
        {
            logger?.LogDebug("DbUp: database is already up to date");
        }

        return result.Successful;
    }
}
