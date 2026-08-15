using System.ComponentModel.DataAnnotations;
using System.ComponentModel.DataAnnotations.Schema;

namespace papermast.Entities.Models
{
    public class BookEntry
    {
        [Key]
        public uint EntryID { get; set; }

        // Foreign key
        public int UserID { get; set; }          // match AppUser.Id type
        [ForeignKey(nameof(UserID))]
        public AppUser User { get; set; } = null!;

        [StringLength(20)]
        public string? Isbn10 { get; set; }

        [StringLength(20)]
        public string? Isbn13 { get; set; }

        [StringLength(100)]
        public string? Source { get; set; }

        [StringLength(200)]
        public string? SourceBookID { get; set; }

        [StringLength(500)]
        public string Title { get; set; } = null!;

        [StringLength(1000)]
        public string? Authors { get; set; }

        [StringLength(2000)]
        public string? ThumbnailUrl { get; set; }

        public int PageCount { get; set; }

        [StringLength(50)]
        public string? Status { get; set; }

        public int PagesCompleted { get; set; }

        public int PercentCompleted { get; set; }

        public decimal? Rating { get; set; }

        public string? UserReview { get; set; }

        public string? UserInternalReview { get; set; }

        public DateTime? StartDate { get; set; }

        public DateTime? EndDate { get; set; }

        public DateTime CreatedDate { get; set; } = DateTime.UtcNow;

        public DateTime UpdatedDate { get; set; } = DateTime.UtcNow;
    }
}
