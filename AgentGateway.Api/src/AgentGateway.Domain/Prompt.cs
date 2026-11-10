using AgentGateway.Common.Results;
using AgentGateway.Common.Validation;
using AgentGateway.Domain.Params;

namespace AgentGateway.Domain;

/// <summary>A validated prompt with the model profile chosen from its complexity.</summary>
public sealed class Prompt
{
    public const ComplexityLevel DefaultComplexity = ComplexityLevel.Medium;

    public string Text { get; }
    public ModelProfile Profile { get; }
    public string? JsonSchema { get; }

    public static Result<Prompt> Create(PromptParams parameters)
    {
        if (parameters.Validate().ToValidationError() is { } error)
        {
            return error;
        }

        var profile = ModelProfile.For(parameters.Complexity ?? DefaultComplexity);
        return Result.Success(new Prompt(parameters.Prompt, profile, parameters.JsonSchema));
    }

    private Prompt(string text, ModelProfile profile, string? jsonSchema)
    {
        Text = text;
        Profile = profile;
        JsonSchema = jsonSchema;
    }
}
