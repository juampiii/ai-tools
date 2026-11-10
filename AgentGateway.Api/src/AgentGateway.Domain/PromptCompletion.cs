namespace AgentGateway.Domain;

/// <summary>The answer of the model to a prompt, with its token usage and cost in USD.</summary>
public sealed record PromptCompletion(string Text, int InputTokens, int OutputTokens, decimal Cost);
