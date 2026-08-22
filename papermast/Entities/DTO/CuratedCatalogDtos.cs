namespace papermast.Entities.DTO;

public record CuratedCatalogResponse(string Slug, DateTime? PublishedAt, IReadOnlyList<CuratedCatalogSectionDto> Sections);
public record CuratedCatalogSectionDto(string Key, string Title, IReadOnlyList<CuratedCatalogBookDto> Books);
public record CuratedCatalogBookDto(
    string Id, string Title, string[] Authors, string Description, CuratedImageLinksDto ImageLinks,
    string Publisher, CuratedIdentifierDto[] IndustryIdentifiers, string? PublishedDate,
    string Isbn13, DateTime? ReleaseDate, int Position);
public record CuratedIdentifierDto(string Type, string Identifier);
public record CuratedImageLinksDto(string SmallThumbnail, string Thumbnail);
public record CatalogImportErrorDto(int Row, string Field, string Message);
public record CatalogImportPreviewDto(int BatchId, CuratedCatalogResponse Catalog, IReadOnlyList<CatalogImportErrorDto> Errors);
public record CoverOverrideRequest(string Url);
public record AddCatalogBookRequest(string Isbn, string Section);
