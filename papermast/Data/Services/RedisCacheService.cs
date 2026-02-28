using Microsoft.Extensions.Caching.Distributed;
using papermast.Helpers;

namespace papermast.Data.Services
{
    public interface IRedisCacheService
    {
        Task<T?> GetOrCreateAsoluteTTLAsync<T>(string key, Func<Task<T>> factory, TimeSpan ttl);
    }

    public class RedisCacheService : IRedisCacheService
    {
        private readonly IDistributedCache _cache;

        public RedisCacheService(IDistributedCache cache)
        {
            _cache = cache;
        }

        public async Task<T?> GetOrCreateAsoluteTTLAsync<T>(string key, Func<Task<T>> factory, TimeSpan ttl)
        {
            var cached = await _cache.GetAsync<T>(key);
            if (cached is not null && cached is T value && (value is not string s || !string.IsNullOrEmpty(s))) return cached;

            var result = await factory();

            if (result is not null) await _cache.SetAsync(key, result, ttl);
            
            return result;
        }
    }
}
