namespace AgentGateway.Common.Results;

/// <summary>Outcome of an operation without a value: command handlers, domain event handlers and infrastructure helpers.</summary>
public class Result
{
    public Error? Error { get; }
    public bool IsSuccess => Error is null;
    public bool IsFailure => !IsSuccess;

    protected Result(Error? error)
    {
        Error = error;
    }

    public static Result Success() => new(null);

    public static Result Failure(Error error) => new(error);

    public static Result<T> Success<T>(T value) => Result<T>.Success(value);

    public static Result<T> Failure<T>(Error error) => Result<T>.Failure(error);

    public static implicit operator Result(Error error) => Failure(error);
}

/// <summary>Outcome of an operation that returns a value on success.</summary>
public sealed class Result<T> : Result
{
    private readonly T? _value;

    /// <summary>The value of a successful result. Throws when the result is a failure.</summary>
    public T Value => IsSuccess
        ? _value!
        : throw new InvalidOperationException($"A failed result has no value. Error: {Error!.Type} - {Error.Message}");

    private Result(T? value, Error? error) : base(error)
    {
        _value = value;
    }

    public static Result<T> Success(T value) => new(value, null);

    public new static Result<T> Failure(Error error) => new(default, error);

    public static implicit operator Result<T>(Error error) => Failure(error);
}
