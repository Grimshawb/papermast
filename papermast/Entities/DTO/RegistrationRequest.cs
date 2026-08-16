using System.ComponentModel.DataAnnotations;

namespace papermast
{
    public class RegistrationRequest
    {
        [Required, StringLength(64, MinimumLength = 2)]
        public string? Username {  get; set; }

        [Required, StringLength(100)]
        public string? FirstName {  get; set; }

        [Required, StringLength(100)]
        public string? LastName {  get; set; }

        [Required, EmailAddress, StringLength(254)]
        public string? Email {  get; set; }

        [Required, StringLength(128, MinimumLength = 8)]
        public string? Password { get; set; }
    }
}
