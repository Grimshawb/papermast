using Microsoft.AspNetCore.Authorization;
using Microsoft.AspNetCore.Mvc;
using Microsoft.AspNetCore.RateLimiting;
using papermast.Data.Services;
using papermast.Entities.DTO;

namespace papermast.Controllers;

[Route("api/librarian")]
[ApiController]
[Authorize]
[EnableRateLimiting("librarian")]
public sealed class LibrarianController(ILibrarianRecommendationService librarian) : ControllerBase
{
    [HttpPost("recommendations")]
    [ProducesResponseType<LibrarianResponse>(StatusCodes.Status200OK)]
    [ProducesResponseType<ProblemDetails>(StatusCodes.Status400BadRequest)]
    [ProducesResponseType(StatusCodes.Status401Unauthorized)]
    [ProducesResponseType<ProblemDetails>(StatusCodes.Status429TooManyRequests)]
    [ProducesResponseType<ProblemDetails>(StatusCodes.Status503ServiceUnavailable)]
    public async Task<ActionResult<LibrarianResponse>> Recommend(
        [FromBody] LibrarianRequest request,
        CancellationToken cancellationToken)
    {
        var query = LibrarianRecommendationService.NormalizeQuery(request.Query);
        if (query.Length is < 3 or > 500)
        {
            ModelState.AddModelError(nameof(request.Query), "Query must be between 3 and 500 characters after trimming.");
            return ValidationProblem(ModelState);
        }

        try
        {
            return Ok(await librarian.Recommend(query, request.ResultCount, cancellationToken));
        }
        catch (LibrarianUnavailableException)
        {
            Response.Headers.RetryAfter = "30";
            return Problem(
                statusCode: StatusCodes.Status503ServiceUnavailable,
                title: "The librarian is temporarily unavailable.",
                detail: "Please try again shortly.");
        }
    }
}
