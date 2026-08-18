namespace papermast.Entities.Models;

public class ApiRequestLog
{
    public ulong ApiRequestLogID { get; set; }
    public DateTimeOffset StartedAtUtc { get; set; }
    public string ApiName { get; set; } = string.Empty;
    public string Direction { get; set; } = string.Empty;
    public string Method { get; set; } = string.Empty;
    public string Route { get; set; } = string.Empty;
    public int StatusCode { get; set; }
    public double DurationMs { get; set; }
    public string ActorType { get; set; } = string.Empty;
    public string ActorId { get; set; } = string.Empty;
    public string? QueryParameterNames { get; set; }
    public string? ClientIp { get; set; }
    public string? UserAgent { get; set; }
    public string TraceId { get; set; } = string.Empty;
    public string? ErrorType { get; set; }
    public string? ErrorMessage { get; set; }
}
