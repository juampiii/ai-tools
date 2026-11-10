using System.ComponentModel.DataAnnotations;

namespace AgentGateway.Infrastructure.ClaudeCode;

public class ClaudeCodeOptions
{
    public const string SectionName = "Claude";

    /// <summary>Folder where the Claude Code CLI runs. The client creates it when it does not exist.</summary>
    [Required]
    public string WorkingDirectory { get; set; } = Path.Combine(AppContext.BaseDirectory, "workspace");
}
