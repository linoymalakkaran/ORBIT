using AdPorts.AiPortal.Application.Common.Interfaces;
using Microsoft.AspNetCore.Http;
using System.Security.Claims;

namespace AdPorts.AiPortal.Infrastructure.Identity;

public class CurrentUserService(IHttpContextAccessor httpContextAccessor) : ICurrentUser
{
    private ClaimsPrincipal? User => httpContextAccessor.HttpContext?.User;

    public bool IsAuthenticated => User?.Identity?.IsAuthenticated ?? false;

    public Guid Id
    {
        get
        {
            var sub = User?.FindFirstValue("sub") ?? User?.FindFirstValue(ClaimTypes.NameIdentifier);
            return Guid.TryParse(sub, out var id) ? id : Guid.Empty;
        }
    }

    public string Username => User?.FindFirstValue("preferred_username")
                           ?? User?.FindFirstValue(ClaimTypes.Name)
                           ?? "anonymous";

    public string Email => User?.FindFirstValue("email")
                        ?? User?.FindFirstValue(ClaimTypes.Email)
                        ?? string.Empty;

    public string[] Groups => User?.Claims
        .Where(c => c.Type == "groups")
        .Select(c => c.Value)
        .ToArray() ?? [];

    public string[] Roles => User?.Claims
        .Where(c => c.Type == ClaimTypes.Role || c.Type == "roles")
        .Select(c => c.Value)
        .ToArray() ?? [];
}
