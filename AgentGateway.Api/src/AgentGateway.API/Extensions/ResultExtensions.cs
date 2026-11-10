using AgentGateway.Common.Results;
using Microsoft.AspNetCore.Http.Json;
using Microsoft.Extensions.Options;

namespace AgentGateway.API.Extensions;

/// <summary>Minimal API counterpart of the controller <c>ToActionResult</c> mapping.</summary>
public static class ResultExtensions
{
    extension(Result result)
    {
        /// <summary>Success becomes 204 No Content. Errors become ProblemDetails.</summary>
        public IResult ToHttpResult()
        {
            return result.IsSuccess
                ? TypedResults.NoContent()
                : ToProblem(result.Error!);
        }
    }

    extension<T>(Result<T> result)
    {
        /// <summary>Success becomes 200 OK, or the <paramref name="onSuccess"/> result. Errors become ProblemDetails.</summary>
        public IResult ToHttpResult(Func<T, IResult>? onSuccess = null)
        {
            if (result.IsFailure)
            {
                return ToProblem(result.Error!);
            }

            return onSuccess is not null
                ? onSuccess(result.Value)
                : TypedResults.Ok(result.Value);
        }
    }

    private static IResult ToProblem(Error error)
    {
        return error.Type switch
        {
            ErrorType.Validation => new ValidationProblemResult(error.ValidationErrors),
            ErrorType.BadRequest => TypedResults.Problem(error.Message, statusCode: StatusCodes.Status400BadRequest),
            ErrorType.NotFound => TypedResults.Problem(error.Message, statusCode: StatusCodes.Status404NotFound),
            ErrorType.Conflict => TypedResults.Problem(error.Message, statusCode: StatusCodes.Status409Conflict),
            ErrorType.ExternalFailure => TypedResults.Problem(error.Message, statusCode: StatusCodes.Status502BadGateway),
            _ => TypedResults.Problem(error.Message, statusCode: StatusCodes.Status500InternalServerError)
        };
    }

    /// <summary>Converts C# property paths (<c>Steps[0].Text</c>) to the JSON names the client sent (<c>steps[0].text</c>).</summary>
    private sealed class ValidationProblemResult(IReadOnlyDictionary<string, string[]> errors) : IResult
    {
        public Task ExecuteAsync(HttpContext httpContext)
        {
            var namingPolicy = httpContext.RequestServices
                .GetRequiredService<IOptions<JsonOptions>>().Value.SerializerOptions.PropertyNamingPolicy;

            var jsonErrors = errors
                .GroupBy(e => namingPolicy is null
                    ? e.Key
                    : string.Join('.', e.Key.Split('.').Select(namingPolicy.ConvertName)))
                .ToDictionary(g => g.Key, g => g.SelectMany(e => e.Value).ToArray());

            return TypedResults.ValidationProblem(jsonErrors).ExecuteAsync(httpContext);
        }
    }
}
