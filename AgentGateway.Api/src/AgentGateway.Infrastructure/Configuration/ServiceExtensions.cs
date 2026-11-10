using AgentGateway.Application.Common.Interfaces;
using AgentGateway.Infrastructure.ClaudeCode;
using Microsoft.Extensions.Configuration;
using Microsoft.Extensions.DependencyInjection;

namespace AgentGateway.Infrastructure.Configuration;

public static class ServiceExtensions
{
    extension(IServiceCollection services)
    {
        public IServiceCollection AddInfrastructure(IConfiguration configuration)
        {
            services.AddOptions<ClaudeCodeOptions>()
                .Bind(configuration.GetSection(ClaudeCodeOptions.SectionName))
                .ValidateDataAnnotations()
                .ValidateOnStart();

            services.AddScoped<IPromptExecutor, ClaudeCodePromptExecutor>();

            return services;
        }
    }
}
