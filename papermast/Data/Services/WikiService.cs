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
        public Task<string> SearchAuthor(string author);
    }

    public class WikiService : IWikiService
    {
        private readonly IHttpClientFactory _httpClientFactory;
        private readonly IConfiguration _config;
        private readonly IDistributedCache _cache;

        public WikiService(IConfiguration config, IHttpClientFactory httpClientFactory,
                           IDistributedCache cache)
        {
            _config = config;
            _httpClientFactory = httpClientFactory;
            _cache = cache;
        }

        public async Task<string> SearchAuthor(string author)
        {
            var header = _config["Wiki:RequestHeader"];
            var url = _config["Wiki:ApiUrl"];
            author = author.Trim().Replace("_", " ");

            var cacheKey = $"wiki:author:{author}";
            var cached = await _cache.GetAsync<string>(cacheKey);
            if (!string.IsNullOrEmpty(cached)) return cached; // Cache hit

            var client = _httpClientFactory.CreateClient();
            client.DefaultRequestHeaders.UserAgent.ParseAdd(header);
            var response = await client.GetAsync($"{url}/{author}"); // Cache Miss

            if (!response.IsSuccessStatusCode) return string.Empty;

            var content = await response.Content.ReadAsStringAsync();
            await _cache.SetAsync(cacheKey, content, TimeSpan.FromHours(24)); // Cache
            return content;
        }
            
    }
}
