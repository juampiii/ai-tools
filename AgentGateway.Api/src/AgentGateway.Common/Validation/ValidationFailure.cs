namespace AgentGateway.Common.Validation;

/// <summary>One broken rule. <see cref="PropertyName"/> uses the C# name; the API converts it to the JSON name.</summary>
public sealed record ValidationFailure(string PropertyName, string Message);
