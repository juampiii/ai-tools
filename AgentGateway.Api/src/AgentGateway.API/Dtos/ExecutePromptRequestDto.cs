using System.Text.Json;
using AgentGateway.Domain;

namespace AgentGateway.API.Dtos;

/// <param name="Complexity">Optional. Defaults to <see cref="ComplexityLevel.Medium"/>.</param>
/// <param name="JsonSchema">Optional JSON schema that the answer must follow.</param>
public sealed record ExecutePromptRequestDto(string Prompt, ComplexityLevel? Complexity, JsonElement? JsonSchema);
