using System.ComponentModel.DataAnnotations;

namespace papermast
{
    public class LoginRequest
    {
        [Required, EmailAddress, StringLength(254)]
        public string? Email { get; set; }

        [Required, StringLength(128)]
        public string? Password { get; set; }
    }
}
