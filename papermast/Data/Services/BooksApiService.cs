using Microsoft.AspNetCore.WebUtilities;

namespace papermast.Data.Services
{

    public interface IBooksApiService
    {
        public Task<string?> DailyAuthorSearch(string? text, string? intitle, string? inauthor, string? subject, string? isbn);
        public Task<string?> Search(string? text, string? intitle, string? inauthor, string? subject, string? isbn);
    }

    public class BooksApiService: IBooksApiService
    {
        private readonly IConfiguration _config;
        private readonly IRedisCacheService _cache;
        private readonly IHttpClientFactory _httpClientFactory;

        public BooksApiService(IConfiguration config, IRedisCacheService cache, IHttpClientFactory httpClientFactory)
        {
            _config = config;
            _cache = cache;
            _httpClientFactory = httpClientFactory;
        }

        public async Task<string?> DailyAuthorSearch(string? text, string? intitle, string? inauthor, string? subject, string? isbn)
        {
            if (!string.IsNullOrEmpty(inauthor))
            {
                return await _cache.GetOrCreateAsoluteTTLAsync<string?>($"Daily:{inauthor!}", 
                    async () => await apiSearch(text!, intitle!, inauthor!, subject!, isbn!), 
                    TimeSpan.FromDays(1));
            }
            return string.Empty;
        }

        public async Task<string?> Search(string? text, string? intitle, string? inauthor, string? subject, string? isbn)
        {
            return await apiSearch(text, intitle, inauthor, subject, isbn);
        }

        private async Task<string?> apiSearch(string? text, string? intitle, string? inauthor, string? subject, string? isbn)
        {
            var apiKey = _config["GoogleBooks:ApiKey"];
            var apiUrl = _config["GoogleBooks:ApiUrl"];
            var queryParts = new List<string>();

            if (!string.IsNullOrEmpty(text)) queryParts.Add($"q:{text}");
            if (!string.IsNullOrEmpty(intitle)) queryParts.Add($"intitle:{intitle}");
            if (!string.IsNullOrEmpty(inauthor)) queryParts.Add($"inauthor:{inauthor}");
            if (!string.IsNullOrEmpty(subject)) queryParts.Add($"subject:{subject}");
            if (!string.IsNullOrEmpty(isbn)) queryParts.Add($"isbn:{isbn}");

            var query = queryParts.Count > 0 ? $"{string.Join("&", queryParts)}" : "";
            if (string.IsNullOrEmpty(query)) throw new Exception("Cannot Search With Empty Query");

            var queryParams = new Dictionary<string, string?>
            {
                ["q"] = query,
                ["orderBy"] = "relevance",
                ["startIndex"] = "0",
                ["maxResults"] = "40",
                ["key"] = apiKey,
            };
            var url = QueryHelpers.AddQueryString(apiUrl, queryParams);
            var client = _httpClientFactory.CreateClient();
            var response = await client.GetAsync(url);
            //var response = await client.GetAsync($"{apiUrl}{query}&key={apiKey}");
            if (!response.IsSuccessStatusCode) throw new Exception($"Error Searching For Books: {response.StatusCode}");

            return await response.Content.ReadAsStringAsync();
        }
    }
}
