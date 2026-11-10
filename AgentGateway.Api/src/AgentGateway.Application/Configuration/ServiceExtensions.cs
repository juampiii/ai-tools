using System.Reflection;
using AgentGateway.Application.Common.Messaging;
using Microsoft.Extensions.DependencyInjection;

namespace AgentGateway.Application.Configuration;

public static class ServiceExtensions
{
    private static readonly Type[] HandlerInterfaceTypes =
    [
        typeof(ICommandHandler<>),
        typeof(ICommandHandler<,>),
        typeof(IQueryHandler<,>)
    ];

    extension(IServiceCollection services)
    {
        public IServiceCollection AddApplicationServices()
        {
            var assembly = Assembly.GetExecutingAssembly();

            services.AddRequestHandlers(assembly);

            return services;
        }

        private IServiceCollection AddRequestHandlers(Assembly assembly)
        {
            var handlerTypes = assembly.GetTypes()
                .Where(t => t is { IsAbstract: false, IsInterface: false });

            foreach (var handlerType in handlerTypes)
            {
                var closedInterfaces = handlerType.GetInterfaces()
                    .Where(i => i.IsGenericType && HandlerInterfaceTypes.Contains(i.GetGenericTypeDefinition()));

                foreach (var closedInterface in closedInterfaces)
                {
                    services.AddScoped(closedInterface, handlerType);
                }
            }

            services.AddScoped<ISender, Sender>();

            return services;
        }
    }
}
