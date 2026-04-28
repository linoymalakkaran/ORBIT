using Confluent.Kafka;
using Microsoft.Extensions.Logging;
using Microsoft.Extensions.Options;
using System.Text.Json;

namespace AdPorts.AiPortal.Infrastructure.Messaging;

public interface IEventPublisher
{
    Task PublishAsync<T>(string topic, string key, T payload, CancellationToken ct = default);
}

public class KafkaOptions
{
    public string BootstrapServers { get; set; } = default!;
    public string ProducerGroupId  { get; set; } = default!;
}

public class KafkaEventPublisher(IOptions<KafkaOptions> opts, ILogger<KafkaEventPublisher> logger)
    : IEventPublisher, IDisposable
{
    private readonly IProducer<string, string> _producer = new ProducerBuilder<string, string>(
        new ProducerConfig { BootstrapServers = opts.Value.BootstrapServers })
        .Build();

    public async Task PublishAsync<T>(string topic, string key, T payload, CancellationToken ct = default)
    {
        var value = JsonSerializer.Serialize(payload);
        var message = new Message<string, string> { Key = key, Value = value };
        var result = await _producer.ProduceAsync(topic, message, ct);
        logger.LogDebug("Published to {Topic} offset {Offset}", topic, result.Offset);
    }

    public void Dispose() => _producer.Dispose();
}
