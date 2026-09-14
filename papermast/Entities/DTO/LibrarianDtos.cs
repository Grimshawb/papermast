using System.ComponentModel.DataAnnotations;

namespace papermast.Entities.DTO;

public sealed record LibrarianRequest(
    [param: Required, StringLength(500, MinimumLength = 3)] string Query,
    [param: Range(3, 5)] int ResultCount = 5);

public sealed record LibrarianResponse(
    IReadOnlyList<LibrarianRecommendation> Recommendations,
    double ElapsedMs);

public sealed record LibrarianRecommendation(
    string WorkKey,
    string Title,
    IReadOnlyList<string> Authors,
    IReadOnlyList<string> Genres,
    string Description,
    string? EditionKey,
    IReadOnlyList<int> CoverIds,
    IReadOnlyList<string> Isbn10,
    IReadOnlyList<string> Isbn13,
    string? PublicationDate,
    int? PageCount,
    string Reason);
