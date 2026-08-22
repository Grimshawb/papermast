namespace papermast.Entities.Models;

public class CuratedCatalogBatch
{
    public int CuratedCatalogBatchID { get; set; }
    public string GenreSlug { get; set; } = string.Empty;
    public string Status { get; set; } = "Draft";
    public DateTime CreatedAtUtc { get; set; } = DateTime.UtcNow;
    public DateTime? PublishedAtUtc { get; set; }
    public string CreatedByUserID { get; set; } = string.Empty;
    public ICollection<CuratedCatalogBook> Books { get; set; } = [];
}
