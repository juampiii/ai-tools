namespace AgentGateway.Common.Results;

public sealed record Error(ErrorType Type, string Message)
{
    private static readonly IReadOnlyDictionary<string, string[]> _noValidationErrors = new Dictionary<string, string[]>();

    /// <summary>Property path to messages. Only filled when <see cref="Type"/> is <see cref="ErrorType.Validation"/>.</summary>
    public IReadOnlyDictionary<string, string[]> ValidationErrors { get; private init; } = _noValidationErrors;

    public static Error Failure(string message) => new(ErrorType.Failure, message);

    public static Error BadRequest(string message) => new(ErrorType.BadRequest, message);

    public static Error NotFound(string message) => new(ErrorType.NotFound, message);

    public static Error Conflict(string message) => new(ErrorType.Conflict, message);

    public static Error ExternalFailure(string message) => new(ErrorType.ExternalFailure, message);

    public static Error Validation(IReadOnlyDictionary<string, string[]> validationErrors) =>
        new(ErrorType.Validation, "One or more validation errors occurred.") { ValidationErrors = validationErrors };
}
