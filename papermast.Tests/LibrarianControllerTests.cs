using Microsoft.AspNetCore.Authorization;
using Microsoft.AspNetCore.Http;
using Microsoft.AspNetCore.Mvc;
using papermast.Controllers;
using papermast.Data.Services;
using papermast.Entities.DTO;
using Xunit;

namespace papermast.Tests;

public sealed class LibrarianControllerTests
{
    [Fact]
    public void Controller_requires_authentication()
    {
        var attribute = Assert.Single(
            typeof(LibrarianController).GetCustomAttributes(typeof(AuthorizeAttribute), inherit: true));

        Assert.IsType<AuthorizeAttribute>(attribute);
    }

    [Fact]
    public async Task Recommend_returns_503_without_leaking_internal_failure()
    {
        var controller = new LibrarianController(new UnavailableService())
        {
            ControllerContext = new ControllerContext { HttpContext = new DefaultHttpContext() }
        };

        var result = await controller.Recommend(
            new LibrarianRequest("funny and weird", 5),
            CancellationToken.None);

        var problem = Assert.IsType<ObjectResult>(result.Result);
        Assert.Equal(StatusCodes.Status503ServiceUnavailable, problem.StatusCode);
        var details = Assert.IsType<ProblemDetails>(problem.Value);
        Assert.Equal("Please try again shortly.", details.Detail);
        Assert.Equal("30", controller.Response.Headers.RetryAfter);
    }

    [Fact]
    public async Task Recommend_rejects_whitespace_only_query()
    {
        var controller = new LibrarianController(new UnavailableService())
        {
            ControllerContext = new ControllerContext { HttpContext = new DefaultHttpContext() }
        };

        var result = await controller.Recommend(new LibrarianRequest("   ", 5), CancellationToken.None);

        Assert.IsType<ObjectResult>(result.Result);
        Assert.False(controller.ModelState.IsValid);
    }

    private sealed class UnavailableService : ILibrarianRecommendationService
    {
        public Task<LibrarianResponse> Recommend(string query, int resultCount, CancellationToken cancellationToken) =>
            throw new LibrarianUnavailableException("Internal upstream detail that must not reach the browser.");
    }
}
