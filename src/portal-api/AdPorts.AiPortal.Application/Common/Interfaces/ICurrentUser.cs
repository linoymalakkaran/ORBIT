namespace AdPorts.AiPortal.Application.Common.Interfaces;

public interface ICurrentUser
{
    Guid   Id       { get; }
    string Username { get; }
    string Email    { get; }
    string[] Groups { get; }
    string[] Roles  { get; }
    bool IsAuthenticated { get; }
}
