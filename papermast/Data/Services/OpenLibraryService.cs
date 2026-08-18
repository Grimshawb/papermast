using Microsoft.AspNetCore.WebUtilities;

namespace papermast.Data.Services
{
    public interface IOpenLibraryService
    {
        Task<string?> GetPopularBySubject(string subject);
    }

    public class OpenLibraryService : IOpenLibraryService
    {
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

            var client = _httpClientFactory.CreateClient();
            client.DefaultRequestHeaders.UserAgent.ParseAdd(
                _config["Wiki:RequestHeader"] ?? "PaperMast/1.0");
            var response = await client.GetAsync(QueryHelpers.AddQueryString(apiUrl, queryParams));
            if (!response.IsSuccessStatusCode)
                throw new Exception($"Error searching Open Library: {response.StatusCode}");

            return await response.Content.ReadAsStringAsync();
        }
    }
}
