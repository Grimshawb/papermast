namespace papermast.Entities.Models;

public class CuratedCatalogBook
{
    public int CuratedCatalogBookID { get; set; }
    public int CuratedCatalogBatchID { get; set; }
    public CuratedCatalogBatch Batch { get; set; } = null!;
    public string Section { get; set; } = string.Empty;
    public int Position { get; set; }
    public string Isbn13 { get; set; } = string.Empty;
    public string SourceBookID { get; set; } = string.Empty;
    public string Title { get; set; } = string.Empty;
    public string AuthorsJson { get; set; } = "[]";
    public string Description { get; set; } = string.Empty;
    public string CoverUrl { get; set; } = string.Empty;
    public string Publisher { get; set; } = string.Empty;
    public string IdentifiersJson { get; set; } = "[]";
    public string? PublishedDate { get; set; }
    public DateTime? ReleaseDate { get; set; }
}
