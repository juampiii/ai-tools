using AgentGateway.Common.Results;

namespace AgentGateway.Application.Common.Messaging;

/// <summary>Sends a command or query to its single registered handler.</summary>
public interface ISender
{
    Task<Result> SendAsync(ICommand command, CancellationToken cancellationToken = default);

    Task<Result<TResponse>> SendAsync<TResponse>(ICommand<TResponse> command, CancellationToken cancellationToken = default);

    Task<Result<TResponse>> SendAsync<TResponse>(IQuery<TResponse> query, CancellationToken cancellationToken = default);
}
