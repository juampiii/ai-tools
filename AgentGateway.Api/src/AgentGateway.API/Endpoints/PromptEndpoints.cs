using AgentGateway.API.Dtos;
using AgentGateway.API.Extensions;
using AgentGateway.Application.Common.Messaging;
using AgentGateway.Application.Features.Prompts;
using AgentGateway.Application.Features.Prompts.Commands.ExecutePrompt;

namespace AgentGateway.API.Endpoints;

public static class PromptEndpoints
{
    extension(IEndpointRouteBuilder app)
    {
        public IEndpointRouteBuilder MapPromptEndpoints()
        {
            var group = app.MapGroup("api/prompts").WithTags("Prompts");

            group.MapPost("", ExecutePromptAsync)
                .WithName("ExecutePrompt")
                .WithSummary("Runs a prompt with the Claude Code CLI and returns the answer with its usage.")
                .Produces<PromptCompletionDto>(StatusCodes.Status200OK)
                .ProducesValidationProblem()
                .ProducesProblem(StatusCodes.Status502BadGateway);

            // TODO: remove the old route when no client calls it anymore.
            app.MapPost("api/llm", ExecutePromptAsync)
                .ExcludeFromDescription();

            return app;
        }
    }

    private static async Task<IResult> ExecutePromptAsync(
        ExecutePromptRequestDto request,
        ISender sender,
        CancellationToken cancellationToken)
    {
        var result = await sender.SendAsync(
            new ExecutePromptFeature.Command(request.Prompt, request.Complexity, request.JsonSchema?.GetRawText()),
            cancellationToken);

        return result.ToHttpResult();
    }
}
