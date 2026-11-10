using AgentGateway.Common.Validation;

namespace AgentGateway.Domain.Params;

/// <param name="JsonSchema">Optional raw JSON schema that the answer must follow.</param>
public sealed record PromptParams(string Prompt, ComplexityLevel? Complexity, string? JsonSchema) : IValidatable
{
    public IEnumerable<ValidationFailure> Validate()
    {
        if (string.IsNullOrWhiteSpace(Prompt))
        {
            yield return new ValidationFailure(nameof(Prompt), "Prompt is required.");
        }

        if (Complexity is { } complexity && !Enum.IsDefined(complexity))
        {
            yield return new ValidationFailure(nameof(Complexity), "Complexity is not a valid level.");
        }

        if (JsonSchema is not null && string.IsNullOrWhiteSpace(JsonSchema))
        {
            yield return new ValidationFailure(nameof(JsonSchema), "JsonSchema must not be empty.");
        }
    }
}
