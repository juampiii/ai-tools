using AgentGateway.Common.Results;
using AgentGateway.Domain;

namespace AgentGateway.Application.Common.Interfaces;

/// <summary>Runs a prompt against a language model.</summary>
public interface IPromptExecutor
{
    Task<Result<PromptCompletion>> ExecuteAsync(Prompt prompt, CancellationToken cancellationToken = default);
}
