namespace AgentGateway.Domain;

/// <summary>Claude model and reasoning effort used to run a prompt.</summary>
public sealed record ModelProfile(string Model, string Effort)
{
    public static ModelProfile For(ComplexityLevel complexity)
    {
        return complexity switch
        {
            ComplexityLevel.Low => new ModelProfile("claude-haiku-5-5", "low"),
            ComplexityLevel.Medium => new ModelProfile("claude-sonnet-5-5", "medium"),
            ComplexityLevel.High => new ModelProfile("claude-sonnet-5-5", "high"),
            ComplexityLevel.VeryHigh => new ModelProfile("claude-opus-5-5", "high"),
            ComplexityLevel.Max => new ModelProfile("claude-opus-5-5", "max"),
            _ => throw new ArgumentOutOfRangeException(nameof(complexity), complexity, "Unknown complexity level.")
        };
    }
}
