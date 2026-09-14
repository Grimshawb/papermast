using Microsoft.Extensions.Caching.Distributed;
using System.Text.Json;

namespace papermast.Helpers
{
    public static class DistributedCacheExtensions
    {
        public static async Task SetAsync<T>(
            this IDistributedCache cache,
            string key,
            T value,
            TimeSpan ttl,
            CancellationToken cancellationToken = default)
        {
            var json = JsonSerializer.Serialize(value);
            await cache.SetStringAsync(key, json,
                new DistributedCacheEntryOptions
                {
                    AbsoluteExpirationRelativeToNow = ttl
                }, cancellationToken);
        }

        public static async Task<T?> GetAsync<T>(
            this IDistributedCache cache,
            string key,
            CancellationToken cancellationToken = default)
        {
            var json = await cache.GetStringAsync(key, cancellationToken);
            return json == null ? default : JsonSerializer.Deserialize<T>(json);
        }
    }
}
