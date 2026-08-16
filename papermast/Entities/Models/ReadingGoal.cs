using System.ComponentModel.DataAnnotations;
using System.ComponentModel.DataAnnotations.Schema;

namespace papermast.Entities.Models
{
    public class ReadingGoal
    {
        [Key]
        public uint ReadingGoalID { get; set; }

        public int UserID { get; set; }

        [ForeignKey(nameof(UserID))]
        public AppUser User { get; set; } = null!;

        public int Year { get; set; }

        public int TargetBookCount { get; set; }

        public DateTime UpdatedDate { get; set; } = DateTime.UtcNow;
    }
}
