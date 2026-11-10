namespace AgentGateway.Application.Common.Messaging;

/// <summary>A request that reads state and does not change it. Handled by <see cref="IQueryHandler{TQuery,TResponse}"/>.</summary>
public interface IQuery<TResponse>;
