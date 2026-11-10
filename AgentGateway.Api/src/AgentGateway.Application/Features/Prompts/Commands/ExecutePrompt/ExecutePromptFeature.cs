using AgentGateway.Application.Common.Interfaces;
using AgentGateway.Application.Common.Messaging;
using AgentGateway.Common.Results;
using AgentGateway.Domain;
using AgentGateway.Domain.Params;

namespace AgentGateway.Application.Features.Prompts.Commands.ExecutePrompt;

public static class ExecutePromptFeature
{
    /// <param name="Complexity">Optional. The domain uses <see cref="AgentGateway.Domain.Prompt.DefaultComplexity"/> when it is null.</param>
    /// <param name="JsonSchema">Optional raw JSON schema that the answer must follow.</param>
    public sealed record Command(string Prompt, ComplexityLevel? Complexity, string? JsonSchema) : ICommand<PromptCompletionDto>;

    public sealed class Handler(IPromptExecutor promptExecutor) : ICommandHandler<Command, PromptCompletionDto>
    {
        public async Task<Result<PromptCompletionDto>> HandleAsync(
            Command command,
            CancellationToken cancellationToken = default)
        {
            var promptResult = Prompt.Create(new PromptParams(command.Prompt, command.Complexity, command.JsonSchema));
            if (promptResult.IsFailure)
            {
                return promptResult.Error!;
            }

            var prompt = promptResult.Value;

            var completionResult = await promptExecutor.ExecuteAsync(prompt, cancellationToken);
            if (completionResult.IsFailure)
            {
                return completionResult.Error!;
            }

            return Result.Success(PromptCompletionDto.From(completionResult.Value, prompt.Profile));
        }
    }
}
