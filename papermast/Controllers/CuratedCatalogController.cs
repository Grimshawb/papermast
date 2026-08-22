using Microsoft.AspNetCore.Authorization;
using Microsoft.AspNetCore.Mvc;
using papermast.Data.Services;
using papermast.Entities.DTO;
using System.Security.Claims;

namespace papermast.Controllers;

[Route("api/curated-catalogs")]
[ApiController]
public class CuratedCatalogController(ICuratedCatalogService catalogs) : ControllerBase
{
    private static readonly HashSet<string> SupportedGenres = new(StringComparer.OrdinalIgnoreCase)
    {
        "horror", "fantasy", "science-fiction", "mystery", "thriller", "romance",
        "historical-fiction", "literary-fiction", "biography-memoir", "history", "young-adult"
    };

    [HttpGet("{slug}")]
    public async Task<ActionResult<CuratedCatalogResponse>> Get(string slug) =>
        SupportedGenres.Contains(slug) ? Ok(await catalogs.GetPublished(slug.ToLowerInvariant())) : NotFound();

    [Authorize(AuthenticationSchemes = "Bearer", Roles = "Admin")]
    [HttpGet("{slug}/manage")]
    public async Task<IActionResult> GetForAdmin(string slug)
    {
        if (!SupportedGenres.Contains(slug)) return BadRequest("Unknown genre.");
        var result = await catalogs.GetPublishedForAdmin(slug.ToLowerInvariant());
        return result is null ? NotFound() : Ok(result);
    }

    [Authorize(AuthenticationSchemes = "Bearer", Roles = "Admin")]
    [HttpPost("{slug}/imports")]
    [RequestSizeLimit(2 * 1024 * 1024)]
    public async Task<IActionResult> Import(string slug, [FromForm] string section, IFormFile file)
    {
        if (!SupportedGenres.Contains(slug)) return BadRequest("Unknown genre.");
        section = section.ToLowerInvariant();
        if (section is not ("popular" or "upcoming")) return BadRequest("Unknown catalog section.");
        if (file.Length == 0) return BadRequest(new { errors = new[] { new CatalogImportErrorDto(1, "file", "Choose a non-empty CSV file.") } });
        await using var stream = file.OpenReadStream();
        var (preview, errors) = await catalogs.Import(slug.ToLowerInvariant(), section, stream, User.FindFirstValue(ClaimTypes.NameIdentifier) ?? "unknown");
        return preview is null ? BadRequest(new { errors }) : Ok(preview);
    }

    [Authorize(AuthenticationSchemes = "Bearer", Roles = "Admin")]
    [HttpPost("{slug}/imports/{batchId:int}/publish")]
    public async Task<IActionResult> Publish(string slug, int batchId)
    {
        if (!SupportedGenres.Contains(slug)) return BadRequest("Unknown genre.");
        var result = await catalogs.Publish(slug.ToLowerInvariant(), batchId);
        return result is null ? NotFound("Draft catalog not found.") : Ok(result);
    }

    [Authorize(AuthenticationSchemes = "Bearer", Roles = "Admin")]
    [HttpPut("{slug}/imports/{batchId:int}/books/{isbn}/cover")]
    public async Task<IActionResult> SetCover(string slug, int batchId, string isbn, [FromBody] CoverOverrideRequest request)
    {
        if (!SupportedGenres.Contains(slug)) return BadRequest("Unknown genre.");
        if (string.IsNullOrWhiteSpace(request.Url) || request.Url.Length > 2000 || !Uri.TryCreate(request.Url, UriKind.Absolute, out var uri) || uri.Scheme != Uri.UriSchemeHttps || !string.IsNullOrEmpty(uri.UserInfo))
            return BadRequest(new { message = "Enter a valid HTTPS image URL." });
        var result = await catalogs.SetCoverOverride(slug.ToLowerInvariant(), batchId, isbn, request.Url);
        return result is null ? NotFound("Draft book not found.") : Ok(result);
    }

    [Authorize(AuthenticationSchemes = "Bearer", Roles = "Admin")]
    [HttpDelete("{slug}/imports/{batchId:int}/books/{isbn}/cover")]
    public async Task<IActionResult> RemoveCover(string slug, int batchId, string isbn)
    {
        if (!SupportedGenres.Contains(slug)) return BadRequest("Unknown genre.");
        var result = await catalogs.SetCoverOverride(slug.ToLowerInvariant(), batchId, isbn, null);
        return result is null ? NotFound("Draft book not found.") : Ok(result);
    }

    [Authorize(AuthenticationSchemes = "Bearer", Roles = "Admin")]
    [HttpPost("{slug}/imports/{batchId:int}/books")]
    public async Task<IActionResult> AddBook(string slug, int batchId, [FromBody] AddCatalogBookRequest request)
    {
        if (!SupportedGenres.Contains(slug)) return BadRequest(new { message = "Unknown genre." });
        var section = request.Section?.ToLowerInvariant() ?? string.Empty;
        if (section is not ("popular" or "upcoming")) return BadRequest(new { message = "Unknown catalog section." });
        var (catalog, error) = await catalogs.AddBook(slug.ToLowerInvariant(), batchId, section, request.Isbn ?? string.Empty);
        return catalog is null ? BadRequest(new { message = error }) : Ok(catalog);
    }

    [Authorize(AuthenticationSchemes = "Bearer", Roles = "Admin")]
    [HttpDelete("{slug}/imports/{batchId:int}/books/{isbn}")]
    public async Task<IActionResult> RemoveBook(string slug, int batchId, string isbn)
    {
        if (!SupportedGenres.Contains(slug)) return BadRequest("Unknown genre.");
        var result = await catalogs.RemoveBook(slug.ToLowerInvariant(), batchId, isbn);
        return result is null ? NotFound("Draft book not found.") : Ok(result);
    }
}
