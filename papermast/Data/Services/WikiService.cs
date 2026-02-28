using Microsoft.AspNetCore.Identity;
using Microsoft.AspNetCore.Mvc;
using Microsoft.Extensions.Caching.Distributed;
using Microsoft.Identity.Client;
using papermast.Entities.Models;
using papermast.Helpers;

namespace papermast.Data.Services
{
    public interface IWikiService
    {
        public Task<string?> SearchAuthor(string author);
    }

    public class WikiService : IWikiService
    {
        private readonly IHttpClientFactory _httpClientFactory;
        private readonly IConfiguration _config;
        private readonly IRedisCacheService _cache;

        public WikiService(IConfiguration config, IHttpClientFactory httpClientFactory,
                           IRedisCacheService cache)
        {
            _config = config;
            _httpClientFactory = httpClientFactory;
            _cache = cache;
        }

        public async Task<string?> SearchAuthor(string author)
        {
            author = author.Trim().Replace("_", " ");
            return await _cache.GetOrCreateAsoluteTTLAsync<string>($"wiki:author:{author}", async () =>
                {
                    var client = _httpClientFactory.CreateClient();
                    client.DefaultRequestHeaders.UserAgent.ParseAdd(_config["Wiki:RequestHeader"]);

                    var response = await client.GetAsync($"{_config["Wiki:ApiUrl"]}/{author}");

                    if (!response.IsSuccessStatusCode) return string.Empty;

                    return await response.Content.ReadAsStringAsync();
                }, TimeSpan.FromHours(24));
        }
            
    }
}
