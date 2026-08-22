namespace papermast.Entities.Models;

public class BookMetadata
{
    public int BookMetadataID { get; set; }
    public string Isbn13 { get; set; } = string.Empty;
    public string SourceBookID { get; set; } = string.Empty;
    public string Title { get; set; } = string.Empty;
    public string AuthorsJson { get; set; } = "[]";
    public string Description { get; set; } = string.Empty;
    public string CoverUrl { get; set; } = string.Empty;
    public string? CoverOverrideUrl { get; set; }
    public string Publisher { get; set; } = string.Empty;
    public string IdentifiersJson { get; set; } = "[]";
    public string? PublishedDate { get; set; }
    public string Provider { get; set; } = string.Empty;
    public DateTime RetrievedAtUtc { get; set; } = DateTime.UtcNow;
}
