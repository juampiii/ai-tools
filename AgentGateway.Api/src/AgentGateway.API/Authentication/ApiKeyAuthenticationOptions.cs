using Microsoft.AspNetCore.Authentication;

namespace AgentGateway.API.Authentication;

public class ApiKeyAuthenticationOptions : AuthenticationSchemeOptions
{
    public const string SectionName = "Authentication";
    public const string SchemeName = "ApiKey";
    public const string HeaderName = "X-Api-Key";

    /// <summary>Key that clients send in the <c>X-Api-Key</c> header. Comes from user secrets or the environment.</summary>
    public string ApiKey { get; set; } = string.Empty;
}
