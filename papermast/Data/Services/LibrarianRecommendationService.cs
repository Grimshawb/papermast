using System.Security.Cryptography;
using System.Text;
using Microsoft.Extensions.Caching.Distributed;
using papermast.Entities.DTO;
using papermast.Entities.Options;
using papermast.Helpers;

namespace papermast.Data.Services;

public interface ILibrarianRecommendationService
{
    Task<LibrarianResponse> Recommend(string query, int resultCount, CancellationToken cancellationToken);
}

public sealed class LibrarianRecommendationService(
    ILibrarianClient client,
    IDistributedCache cache,
    LibrarianOptions options,
    ILogger<LibrarianRecommendationService> logger) : ILibrarianRecommendationService
{
    public async Task<LibrarianResponse> Recommend(
        string query,
        int resultCount,
        CancellationToken cancellationToken)
    {
        if (!options.Enabled)
            throw new LibrarianUnavailableException("The librarian feature is not enabled.");

        var normalizedQuery = NormalizeQuery(query);
        var cacheKey = BuildCacheKey(normalizedQuery, resultCount, options.CatalogVersion);

        try
        {
            var cached = await cache.GetAsync<LibrarianResponse>(cacheKey, cancellationToken);
            if (cached is not null) return cached;
        }
        catch (Exception exception) when (exception is not OperationCanceledException)
        {
            logger.LogWarning(exception, "Librarian cache read failed; continuing without cached results.");
        }

        var result = await client.Recommend(normalizedQuery, resultCount, cancellationToken);

        try
        {
            await cache.SetAsync(
                cacheKey,
                result,
                TimeSpan.FromMinutes(options.CacheMinutes),
                cancellationToken);
        }
        catch (Exception exception) when (exception is not OperationCanceledException)
        {
            logger.LogWarning(exception, "Librarian cache write failed; returning uncached results.");
        }

        return result;
    }

    internal static string NormalizeQuery(string query) =>
        string.Join(' ', query.Trim().Split((char[]?)null, StringSplitOptions.RemoveEmptyEntries));

    internal static string BuildCacheKey(string query, int resultCount, string catalogVersion)
    {
        var input = $"{catalogVersion}\n{resultCount}\n{query.ToLowerInvariant()}";
        var hash = Convert.ToHexString(SHA256.HashData(Encoding.UTF8.GetBytes(input))).ToLowerInvariant();
        return $"librarian:recommend:{hash}";
    }
}
