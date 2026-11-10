using AgentGateway.API.Authentication;
using AgentGateway.API.Endpoints;
using Scalar.AspNetCore;
using System.Text.Json.Serialization;

namespace AgentGateway.API.Configuration;

public static class ApiServiceExtensions
{
    extension(IServiceCollection services)
    {
        public IServiceCollection AddApiServices(IConfiguration configuration)
        {
            services.ConfigureHttpJsonOptions(options =>
            {
                options.SerializerOptions.Converters.Add(new JsonStringEnumConverter());
            });

            services.AddProblemDetails();
            services.AddOpenApi(options =>
            {
                options.AddDocumentTransformer<ApiKeyOpenApiTransformer>();
                options.AddOperationTransformer<ApiKeyOpenApiTransformer>();
            });
            services.AddHealthChecks();

            services.AddApiKeyAuthentication(configuration);

            return services;
        }

        private IServiceCollection AddApiKeyAuthentication(IConfiguration configuration)
        {
            services.AddAuthentication(ApiKeyAuthenticationOptions.SchemeName)
                .AddScheme<ApiKeyAuthenticationOptions, ApiKeyAuthenticationHandler>(ApiKeyAuthenticationOptions.SchemeName, null);

            services.AddOptions<ApiKeyAuthenticationOptions>(ApiKeyAuthenticationOptions.SchemeName)
                .Bind(configuration.GetSection(ApiKeyAuthenticationOptions.SectionName))
                .Validate(
                    options => !string.IsNullOrWhiteSpace(options.ApiKey),
                    "Authentication:ApiKey is not configured. Set it with user secrets or the Authentication__ApiKey environment variable.")
                .ValidateOnStart();

            services.AddAuthorization();

            return services;
        }
    }

    extension(WebApplication app)
    {
        public WebApplication UseApiServices()
        {
            app.UseExceptionHandler();
            app.UseStatusCodePages();

            app.UseAuthentication();
            app.UseAuthorization();

            // the API only listens on localhost, so the docs stay available in every environment
            app.MapOpenApi();
            app.MapScalarApiReference();

            app.MapHealthChecks("/health");
            app.MapPromptEndpoints();

            return app;
        }
    }
}
