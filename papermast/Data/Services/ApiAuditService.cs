using System.Threading.Channels;
using Microsoft.EntityFrameworkCore;
using papermast.Entities.Models;

namespace papermast.Data.Services;

public interface IApiAuditSink
{
    bool TryWrite(ApiRequestLog entry);
}

public sealed class ApiAuditQueue : IApiAuditSink
{
    private readonly Channel<ApiRequestLog> _channel = Channel.CreateBounded<ApiRequestLog>(
        new BoundedChannelOptions(10_000)
        {
            SingleReader = true,
            FullMode = BoundedChannelFullMode.Wait
        });

    public ChannelReader<ApiRequestLog> Reader => _channel.Reader;

    public bool TryWrite(ApiRequestLog entry) => _channel.Writer.TryWrite(entry);
}

public sealed class ApiAuditWriterService : BackgroundService
{
    private const int BatchSize = 100;
    private readonly ApiAuditQueue _queue;
    private readonly IServiceScopeFactory _scopeFactory;
    private readonly ILogger<ApiAuditWriterService> _logger;

    public ApiAuditWriterService(
        ApiAuditQueue queue,
        IServiceScopeFactory scopeFactory,
        ILogger<ApiAuditWriterService> logger)
    {
        _queue = queue;
        _scopeFactory = scopeFactory;
        _logger = logger;
    }

    protected override async Task ExecuteAsync(CancellationToken stoppingToken)
    {
        await foreach (var firstEntry in _queue.Reader.ReadAllAsync(stoppingToken))
        {
            var batch = new List<ApiRequestLog>(BatchSize) { firstEntry };
            while (batch.Count < BatchSize && _queue.Reader.TryRead(out var entry))
            {
                batch.Add(entry);
            }

            try
            {
                await using var scope = _scopeFactory.CreateAsyncScope();
                var database = scope.ServiceProvider.GetRequiredService<AppDbContext>();
                database.ApiRequestLogs.AddRange(batch);
                await database.SaveChangesAsync(stoppingToken);
            }
            catch (Exception exception) when (!stoppingToken.IsCancellationRequested)
            {
                _logger.LogError(exception, "Failed to persist {Count} API audit entries", batch.Count);
            }
        }
    }
}

public sealed class ApiAuditRetentionService : BackgroundService
{
    private static readonly TimeSpan RetentionPeriod = TimeSpan.FromDays(90);
    private static readonly TimeSpan CleanupInterval = TimeSpan.FromDays(1);
    private readonly IServiceScopeFactory _scopeFactory;
    private readonly ILogger<ApiAuditRetentionService> _logger;

    public ApiAuditRetentionService(
        IServiceScopeFactory scopeFactory,
        ILogger<ApiAuditRetentionService> logger)
    {
        _scopeFactory = scopeFactory;
        _logger = logger;
    }

    protected override async Task ExecuteAsync(CancellationToken stoppingToken)
    {
        using var timer = new PeriodicTimer(CleanupInterval);
        do
        {
            try
            {
                await using var scope = _scopeFactory.CreateAsyncScope();
                var database = scope.ServiceProvider.GetRequiredService<AppDbContext>();
                var cutoff = DateTimeOffset.UtcNow.Subtract(RetentionPeriod);
                var deleted = await database.ApiRequestLogs
                    .Where(entry => entry.StartedAtUtc < cutoff)
                    .ExecuteDeleteAsync(stoppingToken);
                _logger.LogInformation("Deleted {Count} API audit entries older than {CutoffUtc}", deleted, cutoff);
            }
            catch (Exception exception) when (!stoppingToken.IsCancellationRequested)
            {
                _logger.LogError(exception, "Failed to delete expired API audit entries");
            }
        }
        while (await timer.WaitForNextTickAsync(stoppingToken));
    }
}
