using System.Security.Claims;

namespace papermast.Helpers;

public static class ApiAuditActor
{
    public static (string ActorType, string ActorId) FromPrincipal(ClaimsPrincipal? principal)
    {
        if (principal?.Identity?.IsAuthenticated != true)
        {
            return ("anonymous", "anonymous");
        }

        var clientId = principal.FindFirst("client_id")?.Value
            ?? principal.FindFirst("azp")?.Value;
        if (!string.IsNullOrWhiteSpace(clientId))
        {
            return ("system", clientId);
        }

        var userId = principal.FindFirstValue(ClaimTypes.NameIdentifier)
            ?? principal.FindFirstValue(ClaimTypes.Email)
            ?? principal.Identity.Name
            ?? "unknown";

        return ("user", userId);
    }
}
