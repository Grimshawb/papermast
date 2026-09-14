namespace papermast.Entities.Options;

public sealed class LibrarianOptions
{
    public const string SectionName = "Librarian";

    public bool Enabled { get; set; }
    public string BaseUrl { get; set; } = string.Empty;
    public int RequestTimeoutSeconds { get; set; } = 20;
    public int CacheMinutes { get; set; } = 60;
    public string CatalogVersion { get; set; } = "bge-runtime-v1";

    public void Validate()
    {
        if (RequestTimeoutSeconds is < 1 or > 120)
            throw new InvalidOperationException("Librarian:RequestTimeoutSeconds must be between 1 and 120.");
        if (CacheMinutes is < 1 or > 1440)
            throw new InvalidOperationException("Librarian:CacheMinutes must be between 1 and 1440.");
        if (string.IsNullOrWhiteSpace(CatalogVersion) || CatalogVersion.Length > 100)
            throw new InvalidOperationException("Librarian:CatalogVersion must be between 1 and 100 characters.");
    }
}
