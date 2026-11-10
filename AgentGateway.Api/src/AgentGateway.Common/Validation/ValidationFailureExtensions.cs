using AgentGateway.Common.Results;

namespace AgentGateway.Common.Validation;

public static class ValidationFailureExtensions
{
    extension(IEnumerable<ValidationFailure> failures)
    {
        /// <summary>Groups the failures by property into an <see cref="ErrorType.Validation"/> error, or returns null when there are none.</summary>
        public Error? ToValidationError()
        {
            var errors = failures
                .GroupBy(f => f.PropertyName)
                .ToDictionary(g => g.Key, g => g.Select(f => f.Message).Distinct().ToArray());

            return errors.Count == 0 ? null : Error.Validation(errors);
        }
    }
}
