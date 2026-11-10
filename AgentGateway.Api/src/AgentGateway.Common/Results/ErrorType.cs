namespace AgentGateway.Common.Results;

public enum ErrorType
{
    /// <summary>Something went wrong while processing the request.</summary>
    Failure,

    /// <summary>One or more validation rules failed. The error carries a property-keyed dictionary.</summary>
    Validation,

    /// <summary>The request is not valid for a reason that is not a field validation.</summary>
    BadRequest,

    /// <summary>The requested resource was not found.</summary>
    NotFound,

    /// <summary>The request conflicts with the current state of the resource.</summary>
    Conflict,

    /// <summary>An external dependency, such as the Claude Code CLI, failed or returned an unexpected answer.</summary>
    ExternalFailure
}
