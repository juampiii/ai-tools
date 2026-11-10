namespace AgentGateway.Application.Common.Messaging;

/// <summary>A request that changes state and returns no value. Handled by <see cref="ICommandHandler{TCommand}"/>.</summary>
public interface ICommand;

/// <summary>A request that changes state and returns a value. Handled by <see cref="ICommandHandler{TCommand,TResponse}"/>.</summary>
public interface ICommand<TResponse>;
