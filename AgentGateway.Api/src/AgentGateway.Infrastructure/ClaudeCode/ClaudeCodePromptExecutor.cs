using AgentGateway.Application.Common.Interfaces;
using AgentGateway.Common.Results;
using AgentGateway.Domain;
using Microsoft.Extensions.Options;
using System.Diagnostics;
using System.Text;
using System.Text.Json;

namespace AgentGateway.Infrastructure.ClaudeCode;

/// <summary>Runs a prompt with the Claude Code CLI in print mode and reads its JSON output.</summary>
internal sealed class ClaudeCodePromptExecutor(IOptions<ClaudeCodeOptions> options) : IPromptExecutor
{
    private const string Executable = "claude";

    private static readonly string[] FixedArguments =
    [
        "--output-format", "json",
        "--permission-mode", "dontAsk",
        "--allowedTools", "Read,Edit,Grep,Bash(npm *)",
        "--no-session-persistence",
        "--setting-sources", "project",
        "--strict-mcp-config",
        "--mcp-config", """{"mcpServers":{}}"""
    ];

    public async Task<Result<PromptCompletion>> ExecuteAsync(
        Prompt prompt,
        CancellationToken cancellationToken = default)
    {
        var workingDirectory = options.Value.WorkingDirectory;
        Directory.CreateDirectory(workingDirectory);

        using var process = new Process { StartInfo = BuildStartInfo(prompt, workingDirectory) };
        process.Start();

        var stdoutTask = process.StandardOutput.ReadToEndAsync(cancellationToken);
        var stderrTask = process.StandardError.ReadToEndAsync(cancellationToken);
        await process.WaitForExitAsync(cancellationToken);

        var stdout = await stdoutTask;
        var stderr = await stderrTask;

        if (process.ExitCode != 0)
        {
            return Error.ExternalFailure(string.IsNullOrWhiteSpace(stderr)
                ? $"The Claude Code CLI failed with exit code {process.ExitCode}."
                : stderr);
        }

        return ParseOutput(stdout);
    }

    private static ProcessStartInfo BuildStartInfo(Prompt prompt, string workingDirectory)
    {
        var startInfo = new ProcessStartInfo
        {
            FileName = Executable,
            WorkingDirectory = workingDirectory,
            RedirectStandardOutput = true,
            RedirectStandardError = true,
            StandardOutputEncoding = Encoding.UTF8,
            StandardErrorEncoding = Encoding.UTF8,
            UseShellExecute = false,
            CreateNoWindow = true
        };

        startInfo.ArgumentList.Add("-p");
        startInfo.ArgumentList.Add(prompt.Text);
        startInfo.ArgumentList.Add("--model");
        startInfo.ArgumentList.Add(prompt.Profile.Model);

        foreach (var argument in FixedArguments)
        {
            startInfo.ArgumentList.Add(argument);
        }

        startInfo.ArgumentList.Add("--effort");
        startInfo.ArgumentList.Add(prompt.Profile.Effort);

        if (prompt.JsonSchema is not null)
        {
            startInfo.ArgumentList.Add("--json-schema");
            startInfo.ArgumentList.Add(prompt.JsonSchema);
        }

        return startInfo;
    }

    private static Result<PromptCompletion> ParseOutput(string stdout)
    {
        try
        {
            using var document = JsonDocument.Parse(stdout);
            var root = document.RootElement;
            var usage = root.GetProperty("usage");

            return Result.Success(new PromptCompletion(
                root.GetProperty("result").GetString() ?? string.Empty,
                usage.GetProperty("input_tokens").GetInt32(),
                usage.GetProperty("output_tokens").GetInt32(),
                root.GetProperty("total_cost_usd").GetDecimal()));
        }
        catch (Exception exception) when (exception is JsonException or KeyNotFoundException or InvalidOperationException or FormatException)
        {
            return Error.ExternalFailure($"The Claude Code CLI returned an unexpected output: {exception.Message}");
        }
    }
}
