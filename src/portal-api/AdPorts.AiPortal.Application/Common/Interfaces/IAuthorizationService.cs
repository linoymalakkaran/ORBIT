namespace AdPorts.AiPortal.Application.Common.Interfaces;

public interface IAuthorizationService
{
    Task<bool> CheckAsync(string user, string relation, string resource, CancellationToken ct = default);
    Task WriteAsync(string user, string relation, string resource, CancellationToken ct = default);
    Task DeleteAsync(string user, string relation, string resource, CancellationToken ct = default);
}
