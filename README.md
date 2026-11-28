# AI tools

Personal tools for AI-assisted development: a local HTTP gateway to Claude Code, interactive development workflows, and local MCP integrations.

## Subprojects

| Project | Purpose | Documentation |
| --- | --- | --- |
| AgentGateway.Api | Exposes Claude Code through a local HTTP API, choosing a model and reasoning effort from the requested complexity. | [Setup, configuration, and API usage](AgentGateway.Api/README.md) |
| DevFlow | Uses LangGraph to propose Git branches from work items and commit messages from pending changes, with human review. | [Installation, commands, and workflow diagrams](DevFlow/README.md) |
| MCPs | Contains independently installed local MCP servers for AI clients. | [Integration index](MCPs/README.md) |
| Azure DevOps MCP | Connects an MCP client to Azure DevOps projects, work items, and wikis. | [Installation and PAT configuration](MCPs/AzureDevOps/README.md) |

## Where to start

- To use `start-branch` or `commit-message`, set up [AgentGateway](AgentGateway.Api/README.md) first, then [DevFlow](DevFlow/README.md). DevFlow calls the gateway at `http://localhost:5052/api/prompts` by default.
- To use Azure DevOps from Claude Code, Codex, or another MCP client, follow the [Azure DevOps MCP guide](MCPs/AzureDevOps/README.md). This integration runs independently of AgentGateway and DevFlow.

Each subproject owns its dependencies and setup. There is no repository-wide installation command. Keep credentials in the local storage described by each guide; never commit API keys, PATs, or local secret files.
