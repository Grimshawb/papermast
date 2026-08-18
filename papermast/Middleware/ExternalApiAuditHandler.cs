using System.Diagnostics;
using papermast.Data.Services;
using papermast.Entities.Models;
using papermast.Helpers;

namespace papermast.Middleware;

public sealed class ExternalApiAuditHandler : DelegatingHandler
{
    private readonly IApiAuditSink _auditSink;
    private readonly IHttpContextAccessor _httpContextAccessor;
    private readonly ILogger<ExternalApiAuditHandler> _logger;

    public ExternalApiAuditHandler(
        IApiAuditSink auditSink,
        IHttpContextAccessor httpContextAccessor,
        ILogger<ExternalApiAuditHandler> logger)
    {
        _auditSink = auditSink;
        _httpContextAccessor = httpContextAccessor;
        _logger = logger;
    }

    protected override async Task<HttpResponseMessage> SendAsync(
        HttpRequestMessage request,
        CancellationToken cancellationToken)
    {
        var startedAtUtc = DateTimeOffset.UtcNow;
        var stopwatch = Stopwatch.StartNew();
        var context = _httpContextAccessor.HttpContext;
        Exception? requestException = null;
        HttpResponseMessage? response = null;

        try
        {
            response = await base.SendAsync(request, cancellationToken);
            return response;
        }
        catch (Exception exception)
        {
            requestException = exception;
            throw;
        }
        finally
        {
            stopwatch.Stop();
            var uri = request.RequestUri;
            var (actorType, actorId) = context is null
                ? ("system", "papermast")
                : ApiAuditActor.FromPrincipal(context.User);
            var entry = new ApiRequestLog
            {
                StartedAtUtc = startedAtUtc,
                ApiName = GetApiName(uri),
                Direction = "outbound",
                Method = request.Method.Method,
                Route = Truncate(uri?.AbsolutePath ?? "unknown", 512)!,
                StatusCode = response is null ? StatusCodes.Status500InternalServerError : (int)response.StatusCode,
                DurationMs = stopwatch.Elapsed.TotalMilliseconds,
                ActorType = actorType,
                ActorId = Truncate(actorId, 255)!,
                QueryParameterNames = Truncate(GetQueryParameterNames(uri), 512),
                ClientIp = context?.Connection.RemoteIpAddress?.ToString(),
                UserAgent = Truncate(request.Headers.UserAgent.ToString(), 512),
                TraceId = context?.TraceIdentifier ?? Activity.Current?.TraceId.ToString() ?? Guid.NewGuid().ToString("N"),
                ErrorType = requestException?.GetType().Name,
                // An outbound exception can contain a URI with credential-bearing query values.
                ErrorMessage = requestException is null ? null : "Outbound request failed."
            };

            if (!_auditSink.TryWrite(entry))
            {
                _logger.LogWarning("API audit queue is full; dropped outbound audit entry for {ApiName}", entry.ApiName);
            }
        }
    }

    private static string GetApiName(Uri? uri) => uri?.Host.ToLowerInvariant() switch
    {
        "api.nytimes.com" => "NYT API",
        "openlibrary.org" => "OpenLibrary API",
        "www.googleapis.com" => "Google Books API",
        "en.wikipedia.org" => "Wikipedia API",
        null or "" => "Unknown External API",
        var host => host
    };

    private static string? GetQueryParameterNames(Uri? uri)
    {
        if (uri is null || string.IsNullOrEmpty(uri.Query)) return null;

        return string.Join(',', uri.Query.TrimStart('?')
            .Split('&', StringSplitOptions.RemoveEmptyEntries)
            .Select(part => Uri.UnescapeDataString(part.Split('=', 2)[0]))
            .Distinct(StringComparer.OrdinalIgnoreCase)
            .Order(StringComparer.OrdinalIgnoreCase));
    }

    private static string? Truncate(string? value, int maxLength) =>
        value is not null && value.Length > maxLength ? value[..maxLength] : value;
}
