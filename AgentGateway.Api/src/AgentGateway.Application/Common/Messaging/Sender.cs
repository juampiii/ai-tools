using AgentGateway.Common.Results;
using Microsoft.Extensions.DependencyInjection;

namespace AgentGateway.Application.Common.Messaging;

internal sealed class Sender(IServiceProvider serviceProvider) : ISender
{
    public Task<Result> SendAsync(ICommand command, CancellationToken cancellationToken = default)
    {
        var handlerType = typeof(ICommandHandler<>).MakeGenericType(command.GetType());
        return InvokeHandlerAsync<Result>(handlerType, command, cancellationToken);
    }

    public Task<Result<TResponse>> SendAsync<TResponse>(
        ICommand<TResponse> command,
        CancellationToken cancellationToken = default)
    {
        var handlerType = typeof(ICommandHandler<,>).MakeGenericType(command.GetType(), typeof(TResponse));
        return InvokeHandlerAsync<Result<TResponse>>(handlerType, command, cancellationToken);
    }

    public Task<Result<TResponse>> SendAsync<TResponse>(
        IQuery<TResponse> query,
        CancellationToken cancellationToken = default)
    {
        var handlerType = typeof(IQueryHandler<,>).MakeGenericType(query.GetType(), typeof(TResponse));
        return InvokeHandlerAsync<Result<TResponse>>(handlerType, query, cancellationToken);
    }

    private Task<TResult> InvokeHandlerAsync<TResult>(Type handlerType, object request, CancellationToken cancellationToken)
    {
        // a missing handler is a wiring bug, not a business outcome
        var handler = serviceProvider.GetRequiredService(handlerType);
        var method = handlerType.GetMethod("HandleAsync")!;

        return (Task<TResult>)method.Invoke(handler, [request, cancellationToken])!;
    }
}
