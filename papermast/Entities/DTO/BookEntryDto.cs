namespace papermast.Entities.DTO
{
    public class BookEntryDto
    {
        public uint EntryID { get; set; }
        public string? Source { get; set; }
        public string? SourceBookID { get; set; }
        public string Title { get; set; } = null!;
        public string? Authors { get; set; }
        public string? ThumbnailUrl { get; set; }
        public string? Isbn10 { get; set; }
        public string? Isbn13 { get; set; }
        public string Status { get; set; } = null!;
        public int PageCount { get; set; }
        public int PagesCompleted { get; set; }
        public int PercentCompleted { get; set; }
        public decimal? Rating { get; set; }
        public DateTime? StartDate { get; set; }
        public DateTime? EndDate { get; set; }
        public DateTime CreatedDate { get; set; }
        public DateTime UpdatedDate { get; set; }
    }
}
