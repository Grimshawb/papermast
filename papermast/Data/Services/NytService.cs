using papermast.Entities.Constants;

namespace papermast.Data.Services
{
    public interface INytService
    {
        Task<string?> GetAllBestSellerLists();
    }

    public class NytService : INytService
    {
        private const int NytRefreshHourUtc = 5;

        private readonly IConfiguration _config;
        private readonly IRedisCacheService _cache;
        private readonly IHttpClientFactory _httpClientFactory;

        public NytService(IConfiguration config, IRedisCacheService cache, IHttpClientFactory httpClientFactory)
        {
            _config = config;
            _cache = cache;
            _httpClientFactory = httpClientFactory;
        }

        public async Task<string?> GetAllBestSellerLists()
        {
            return await _cache.GetOrCreateAsoluteTTLAsync<string>(CacheKeys.NYT_ALL_LISTS, async () =>
            {
                var client = _httpClientFactory.CreateClient();

                var response = await client.GetAsync($@"{_config["Nyt:ApiUrl"]}/lists/overview.json?api-key={_config["Nyt:Key"]}");

                if (!response.IsSuccessStatusCode) return string.Empty;

                return await response.Content.ReadAsStringAsync();
            }, GetTimeUntilNextListRefresh(DateTimeOffset.UtcNow));
        }

        internal static TimeSpan GetTimeUntilNextListRefresh(DateTimeOffset now)
        {
            var utcNow = now.ToUniversalTime();
            var daysUntilThursday = ((int)DayOfWeek.Thursday - (int)utcNow.DayOfWeek + 7) % 7;
            var nextRefresh = new DateTimeOffset(
                utcNow.Year,
                utcNow.Month,
                utcNow.Day,
                NytRefreshHourUtc,
                0,
                0,
                TimeSpan.Zero).AddDays(daysUntilThursday);

            if (nextRefresh <= utcNow)
            {
                nextRefresh = nextRefresh.AddDays(7);
            }

            return nextRefresh - utcNow;
        }
    }
}
