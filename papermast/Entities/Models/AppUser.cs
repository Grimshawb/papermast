
using System.ComponentModel.DataAnnotations;

namespace papermast.Entities.Models
{
    public class AppUser
    {
        [Key]
        public int UserID { get; set; }
        public string IdentityUserId { get; set; } = null!;
        public ApplicationUser IdentityUser { get; set; } = null!;
        public string? FirstName { get; set; }
        public string? LastName { get; set; }
    }
}
