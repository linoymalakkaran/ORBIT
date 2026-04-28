using AdPorts.AiPortal.Application.Common.Interfaces;
using Microsoft.Extensions.Configuration;
using OpenFga.Sdk.Api;
using OpenFga.Sdk.Client;
using OpenFga.Sdk.Client.Model;
using OpenFga.Sdk.Model;

namespace AdPorts.AiPortal.Infrastructure.Identity;

public class OpenFgaAuthorizationService : IAuthorizationService
{
    private readonly OpenFgaClient _client;
    private readonly string _storeId;
    private readonly string? _modelId;

    public OpenFgaAuthorizationService(IConfiguration config)
    {
        _storeId = config["OpenFga:StoreId"]!;
        _modelId = config["OpenFga:AuthorizationModelId"];

        var clientConfig = new ClientConfiguration
        {
            ApiUrl  = config["OpenFga:ApiUrl"]!,
            StoreId = _storeId,
            AuthorizationModelId = _modelId
        };
        _client = new OpenFgaClient(clientConfig);
    }

    public async Task<bool> CheckAsync(string user, string relation, string resource, CancellationToken ct = default)
    {
        var response = await _client.Check(new ClientCheckRequest
        {
            User     = user,
            Relation = relation,
            Object   = resource
        }, cancellationToken: ct);
        return response.Allowed ?? false;
    }

    public async Task WriteAsync(string user, string relation, string resource, CancellationToken ct = default)
    {
        await _client.Write(new ClientWriteRequest
        {
            Writes = [new ClientTupleKey { User = user, Relation = relation, Object = resource }]
        }, cancellationToken: ct);
    }

    public async Task DeleteAsync(string user, string relation, string resource, CancellationToken ct = default)
    {
        await _client.Write(new ClientWriteRequest
        {
            Deletes = [new ClientTupleKeyWithoutCondition { User = user, Relation = relation, Object = resource }]
        }, cancellationToken: ct);
    }
}
