using Microsoft.AspNetCore.WebUtilities;
using System.Net;
using System.Text.Json.Nodes;

namespace papermast.Data.Services
{
    public interface IOpenLibraryService
    {
        Task<string?> GetPopularBySubject(string subject);
        Task<IReadOnlyDictionary<string, JsonObject>> GetBooksByIsbn(IEnumerable<string> isbns);
    }

    public class OpenLibraryService : IOpenLibraryService
    {
        private const int BulkBatchSize = 30;
        private static readonly SemaphoreSlim RateGate = new(1, 1);
        private static DateTime _lastRequestUtc = DateTime.MinValue;
        private readonly IConfiguration _config;
        private readonly IHttpClientFactory _httpClientFactory;

        public OpenLibraryService(IConfiguration config, IHttpClientFactory httpClientFactory)
        {
            _config = config;
            _httpClientFactory = httpClientFactory;
        }

        public async Task<string?> GetPopularBySubject(string subject)
        {
            var apiUrl = _config["OpenLibrary:ApiUrl"]
                ?? throw new InvalidOperationException("OpenLibrary:ApiUrl is required.");
            var queryParams = new Dictionary<string, string?>
            {
                ["q"] = $"subject:\"{subject}\" language:eng",
                ["sort"] = "readinglog",
                ["limit"] = "60",
                ["fields"] = "key,title,author_name,cover_i,first_publish_year,ratings_average,ratings_count,readinglog_count"
            };

            using var response = await SendGet(QueryHelpers.AddQueryString(apiUrl, queryParams));
            if (!response.IsSuccessStatusCode)
                throw new Exception($"Error searching Open Library: {response.StatusCode}");

            return await response.Content.ReadAsStringAsync();
        }

        public async Task<IReadOnlyDictionary<string, JsonObject>> GetBooksByIsbn(IEnumerable<string> isbns)
        {
            var apiUrl = _config["OpenLibrary:BooksApiUrl"]
                ?? throw new InvalidOperationException("OpenLibrary:BooksApiUrl is required.");
            var results = new Dictionary<string, JsonObject>(StringComparer.OrdinalIgnoreCase);
            foreach (var batch in isbns.Distinct(StringComparer.OrdinalIgnoreCase).Chunk(BulkBatchSize))
            {
                var bibkeys = string.Join(',', batch.Select(isbn => $"ISBN:{isbn}"));
                var url = QueryHelpers.AddQueryString(apiUrl, new Dictionary<string, string?>
                {
                    ["bibkeys"] = bibkeys, ["format"] = "json", ["jscmd"] = "data"
                });
                using var response = await SendGet(url);
                if (!response.IsSuccessStatusCode)
                    throw new Exception($"Error resolving Open Library ISBNs: {response.StatusCode}");
                if (JsonNode.Parse(await response.Content.ReadAsStringAsync()) is not JsonObject root) continue;
                foreach (var isbn in batch)
                    if (root[$"ISBN:{isbn}"] is JsonObject book) results[isbn] = book;
            }
            return results;
        }

        private async Task<HttpResponseMessage> SendGet(string url)
        {
            await RateGate.WaitAsync();
            try
            {
                var wait = TimeSpan.FromMilliseconds(400) - (DateTime.UtcNow - _lastRequestUtc);
                if (wait > TimeSpan.Zero) await Task.Delay(wait);
                var client = _httpClientFactory.CreateClient();
                client.DefaultRequestHeaders.UserAgent.ParseAdd(
                    _config["OpenLibrary:UserAgent"] ?? throw new InvalidOperationException("OpenLibrary:UserAgent is required."));
                var response = await client.GetAsync(url);
                _lastRequestUtc = DateTime.UtcNow;
                if (response.StatusCode == HttpStatusCode.TooManyRequests)
                {
                    var retryAfter = response.Headers.RetryAfter?.Delta
                        ?? (response.Headers.RetryAfter?.Date - DateTimeOffset.UtcNow)
                        ?? TimeSpan.FromSeconds(1.1);
                    response.Dispose();
                    if (retryAfter > TimeSpan.Zero) await Task.Delay(retryAfter);
                    response = await client.GetAsync(url);
                    _lastRequestUtc = DateTime.UtcNow;
                }
                return response;
            }
            finally { RateGate.Release(); }
        }
    }
}
