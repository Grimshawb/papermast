using System.ComponentModel.DataAnnotations;

namespace papermast.Entities.DTO
{
    public class BookEntryRequest
    {
        [StringLength(100)]
        public string? Source { get; set; }

        [StringLength(200)]
        public string? SourceBookID { get; set; }

        [Required, StringLength(500)]
        public string Title { get; set; } = null!;

        [StringLength(1000)]
        public string? Authors { get; set; }

        [StringLength(2000)]
        public string? ThumbnailUrl { get; set; }

        [StringLength(20)]
        public string? Isbn10 { get; set; }

        [StringLength(20)]
        public string? Isbn13 { get; set; }

        [Required, StringLength(50)]
        public string Status { get; set; } = null!;

        [Range(0, int.MaxValue)]
        public int PageCount { get; set; }
    }
}
