using System.Net;
using System.Net.Http.Json;
using System.Text.Json;
using papermast.Entities.DTO;

namespace papermast.Data.Services;

public interface ILibrarianClient
{
    Task<LibrarianResponse> Recommend(string query, int resultCount, CancellationToken cancellationToken);
}

public sealed class LibrarianClient(HttpClient httpClient) : ILibrarianClient
{
    public async Task<LibrarianResponse> Recommend(
        string query,
        int resultCount,
        CancellationToken cancellationToken)
    {
        HttpResponseMessage response;
        try
        {
            response = await httpClient.PostAsJsonAsync(
                "recommend",
                new { query, result_count = resultCount },
                cancellationToken);
        }
        catch (OperationCanceledException) when (!cancellationToken.IsCancellationRequested)
        {
            throw new LibrarianUnavailableException("The librarian service timed out.");
        }
        catch (HttpRequestException exception)
        {
            throw new LibrarianUnavailableException("The librarian service could not be reached.", exception);
        }

        using (response)
        {
            if (!response.IsSuccessStatusCode)
            {
                var retryable = response.StatusCode is HttpStatusCode.TooManyRequests
                    or HttpStatusCode.ServiceUnavailable
                    or HttpStatusCode.BadGateway
                    or HttpStatusCode.GatewayTimeout;
                throw new LibrarianUnavailableException(retryable
                    ? "The librarian service is temporarily unavailable."
                    : "The librarian service rejected the request.");
            }

            try
            {
                var wireResponse = await response.Content.ReadFromJsonAsync<LibrarianWireResponse>(
                    new JsonSerializerOptions(JsonSerializerDefaults.Web),
                    cancellationToken)
                    ?? throw new LibrarianUnavailableException("The librarian service returned an empty response.");

                return new LibrarianResponse(
                    wireResponse.Recommendations.Select(item => new LibrarianRecommendation(
                        item.WorkKey,
                        item.Title,
                        item.Authors,
                        item.Genres,
                        item.Description,
                        item.EditionKey,
                        item.CoverIds,
                        item.Isbn10,
                        item.Isbn13,
                        item.PublicationDate,
                        item.PageCount,
                        item.Reason)).ToArray(),
                    wireResponse.ElapsedMs);
            }
            catch (JsonException exception)
            {
                throw new LibrarianUnavailableException("The librarian service returned an invalid response.", exception);
            }
        }
    }

    private sealed record LibrarianWireResponse(
        IReadOnlyList<LibrarianWireRecommendation> Recommendations,
        [property: System.Text.Json.Serialization.JsonPropertyName("elapsed_ms")] double ElapsedMs);

    private sealed record LibrarianWireRecommendation(
        [property: System.Text.Json.Serialization.JsonPropertyName("work_key")] string WorkKey,
        string Title,
        IReadOnlyList<string> Authors,
        IReadOnlyList<string> Genres,
        string Description,
        [property: System.Text.Json.Serialization.JsonPropertyName("edition_key")] string? EditionKey,
        [property: System.Text.Json.Serialization.JsonPropertyName("cover_ids")] IReadOnlyList<int> CoverIds,
        [property: System.Text.Json.Serialization.JsonPropertyName("isbn_10")] IReadOnlyList<string> Isbn10,
        [property: System.Text.Json.Serialization.JsonPropertyName("isbn_13")] IReadOnlyList<string> Isbn13,
        [property: System.Text.Json.Serialization.JsonPropertyName("publication_date")] string? PublicationDate,
        [property: System.Text.Json.Serialization.JsonPropertyName("page_count")] int? PageCount,
        string Reason);
}

public sealed class LibrarianUnavailableException : Exception
{
    public LibrarianUnavailableException(string message, Exception? innerException = null)
        : base(message, innerException)
    {
    }
}
