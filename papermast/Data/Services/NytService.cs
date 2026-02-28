namespace papermast.Data.Services
{
    public interface INytService
    {
        Task<string?> GetAllBestSellerLists();
    }

    public class NytService : INytService
    {
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
            return await _cache.GetOrCreateAsoluteTTLAsync<string>($"nyt:all-lists", async () =>
            {
                var client = _httpClientFactory.CreateClient();

                var response = await client.GetAsync($@"{_config["Nyt:ApiUrl"]}/lists/overview.json?api-key={_config["Nyt:Key"]}");

                if (!response.IsSuccessStatusCode) return string.Empty;

                return await response.Content.ReadAsStringAsync();
            }, TimeSpan.FromDays(8));
        }
    }
}
