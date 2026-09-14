using System.ComponentModel.DataAnnotations;
using Xunit;

namespace papermast.Tests;

public sealed class RegistrationRequestTests
{
    [Fact]
    public void Validation_requires_ai_librarian_disclosure_acknowledgment()
    {
        var request = ValidRequest();
        request.AiLibrarianDisclosureAccepted = false;

        var errors = Validate(request);

        Assert.Contains(errors, error =>
            error.MemberNames.Contains(nameof(RegistrationRequest.AiLibrarianDisclosureAccepted)));
    }

    [Fact]
    public void Validation_accepts_ai_librarian_disclosure_acknowledgment()
    {
        var errors = Validate(ValidRequest());

        Assert.DoesNotContain(errors, error =>
            error.MemberNames.Contains(nameof(RegistrationRequest.AiLibrarianDisclosureAccepted)));
    }

    private static RegistrationRequest ValidRequest() => new()
    {
        Username = "ada",
        FirstName = "Ada",
        LastName = "Lovelace",
        Email = "ada@example.com",
        Password = "Secure1!",
        AiLibrarianDisclosureAccepted = true
    };

    private static List<ValidationResult> Validate(RegistrationRequest request)
    {
        var results = new List<ValidationResult>();
        Validator.TryValidateObject(request, new ValidationContext(request), results, validateAllProperties: true);
        return results;
    }

}
