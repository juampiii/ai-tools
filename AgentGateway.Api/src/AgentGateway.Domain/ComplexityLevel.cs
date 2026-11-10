namespace AgentGateway.Domain;

/// <summary>Complexity level used to pick the underlying Claude model and reasoning effort.</summary>
public enum ComplexityLevel
{
    Low,
    Medium,
    High,
    VeryHigh,
    Max
}
