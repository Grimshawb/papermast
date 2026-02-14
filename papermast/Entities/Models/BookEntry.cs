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

        public decimal? Rating { get; set; }

        public string? UserReview { get; set; }

        public string? UserInternalReview { get; set; }

        public DateTime? StartDate { get; set; }

        public DateTime? EndDate { get; set; }
    }
}
