using System.Net;
using System.Text;
using papermast.Data.Services;
using Xunit;

namespace papermast.Tests;

public sealed class LibrarianClientTests
{
    [Fact]
    public async Task Recommend_maps_python_wire_format()
    {
        const string json = """
            {
              "recommendations": [{
                "work_key": "/works/OL1W",
                "title": "A Book",
                "authors": ["An Author"],
                "genres": ["fantasy"],
                "description": "Description",
                "edition_key": "/books/OL1M",
                "cover_ids": [123],
                "isbn_10": ["0123456789"],
                "isbn_13": ["9780123456786"],
                "publication_date": "2001",
                "page_count": 321,
                "reason": "It fits."
              }],
              "elapsed_ms": 12.5
            }
            """;
        var client = CreateClient(HttpStatusCode.OK, json);

        var result = await client.Recommend("fantasy", 3, CancellationToken.None);

        var recommendation = Assert.Single(result.Recommendations);
        Assert.Equal("/works/OL1W", recommendation.WorkKey);
        Assert.Equal("/books/OL1M", recommendation.EditionKey);
        Assert.Equal(321, recommendation.PageCount);
        Assert.Equal(12.5, result.ElapsedMs);
    }

    [Fact]
    public async Task Recommend_translates_upstream_failure()
    {
        var client = CreateClient(HttpStatusCode.ServiceUnavailable, "{}");

        await Assert.ThrowsAsync<LibrarianUnavailableException>(() =>
            client.Recommend("fantasy", 3, CancellationToken.None));
    }

    private static LibrarianClient CreateClient(HttpStatusCode status, string content)
    {
        var httpClient = new HttpClient(new StubHandler(status, content))
        {
            BaseAddress = new Uri("http://librarian/")
        };
        return new LibrarianClient(httpClient);
    }

    private sealed class StubHandler(HttpStatusCode status, string content) : HttpMessageHandler
    {
        protected override Task<HttpResponseMessage> SendAsync(
            HttpRequestMessage request,
            CancellationToken cancellationToken) =>
            Task.FromResult(new HttpResponseMessage(status)
            {
                Content = new StringContent(content, Encoding.UTF8, "application/json")
            });
    }
}
