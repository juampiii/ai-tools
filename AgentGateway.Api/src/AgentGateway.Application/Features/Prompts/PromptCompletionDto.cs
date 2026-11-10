using AgentGateway.Domain;

namespace AgentGateway.Application.Features.Prompts;

public sealed record PromptCompletionDto(string Response, string Model, int InputTokens, int OutputTokens, decimal Cost)
{
    public static PromptCompletionDto From(PromptCompletion completion, ModelProfile profile) =>
        new(completion.Text, profile.Model, completion.InputTokens, completion.OutputTokens, completion.Cost);
}
