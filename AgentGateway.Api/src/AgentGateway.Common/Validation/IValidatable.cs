namespace AgentGateway.Common.Validation;

/// <summary>An input that knows its own rules. Factories and mutators call <see cref="Validate"/> before they change state.</summary>
public interface IValidatable
{
    IEnumerable<ValidationFailure> Validate();
}
