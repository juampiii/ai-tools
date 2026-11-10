using System.Text.Json.Serialization;
using AgentGateway.API.Endpoints;
using Scalar.AspNetCore;

namespace AgentGateway.API.Configuration;

public static class ApiServiceExtensions
{
    extension(IServiceCollection services)
    {
        public IServiceCollection AddApiServices()
        {
            services.ConfigureHttpJsonOptions(options =>
            {
                options.SerializerOptions.Converters.Add(new JsonStringEnumConverter());
            });

            services.AddProblemDetails();
            services.AddOpenApi();
            services.AddHealthChecks();

            return services;
        }
    }

    extension(WebApplication app)
    {
        public WebApplication UseApiServices()
        {
            app.UseExceptionHandler();
            app.UseStatusCodePages();

            // the API only listens on localhost, so the docs stay available in every environment
            app.MapOpenApi();
            app.MapScalarApiReference();

            app.MapHealthChecks("/health");
            app.MapPromptEndpoints();

            return app;
        }
    }
}
