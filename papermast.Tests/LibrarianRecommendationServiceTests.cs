using Microsoft.Extensions.Caching.Distributed;
using Microsoft.Extensions.Caching.Memory;
using Microsoft.Extensions.Logging.Abstractions;
using Microsoft.Extensions.Options;
using papermast.Data.Services;
using papermast.Entities.DTO;
using papermast.Entities.Options;
using Xunit;

namespace papermast.Tests;

public sealed class LibrarianRecommendationServiceTests
{
    [Fact]
    public void NormalizeQuery_collapses_whitespace()
    {
        Assert.Equal("funny and weird", LibrarianRecommendationService.NormalizeQuery("  funny  \n and\tweird "));
    }

    [Fact]
    public void BuildCacheKey_does_not_expose_prompt()
    {
        var key = LibrarianRecommendationService.BuildCacheKey("secret reading mood", 5, "v1");

        Assert.StartsWith("librarian:recommend:", key);
        Assert.DoesNotContain("secret", key);
        Assert.Equal(key, LibrarianRecommendationService.BuildCacheKey("SECRET READING MOOD", 5, "v1"));
        Assert.NotEqual(key, LibrarianRecommendationService.BuildCacheKey("secret reading mood", 3, "v1"));
    }

    [Fact]
    public async Task Recommend_reuses_successful_cached_response()
    {
        var client = new CountingClient();
        var cache = new MemoryDistributedCache(Options.Create(new MemoryDistributedCacheOptions()));
        var service = new LibrarianRecommendationService(
            client,
            cache,
            new LibrarianOptions { Enabled = true, CacheMinutes = 60, CatalogVersion = "v1" },
            NullLogger<LibrarianRecommendationService>.Instance);

        var first = await service.Recommend("funny and weird", 5, CancellationToken.None);
        var second = await service.Recommend(" FUNNY   AND WEIRD ", 5, CancellationToken.None);

        Assert.Equal(1, client.CallCount);
        Assert.Equal(first.ElapsedMs, second.ElapsedMs);
        Assert.Empty(second.Recommendations);
    }

    private sealed class CountingClient : ILibrarianClient
    {
        public int CallCount { get; private set; }

        public Task<LibrarianResponse> Recommend(string query, int resultCount, CancellationToken cancellationToken)
        {
            CallCount++;
            return Task.FromResult(new LibrarianResponse([], 1));
        }
    }
}
