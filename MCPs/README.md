# Local MCP servers

[Back to AI tools](../README.md)

Local Model Context Protocol (MCP) integrations for Codex and other compatible AI clients. Each integration has its own directory, installation instructions, dependencies, and credential storage.

| Integration | Capabilities | Requirements | Documentation |
| --- | --- | --- | --- |
| Azure DevOps | Discover projects and work with cards and wiki pages in `juampidev`. | Windows x64 or ARM64, PowerShell 7, an MCP client, and an organization-scoped PAT. | [Install and configure](AzureDevOps/README.md) |

## Installation

Start with the integration's guide. Azure DevOps installs a portable Node runtime inside its directory and registers a stdio launcher with the MCP client; there is no shared MCP service to start for this repository.

These integrations run independently of [AgentGateway](../AgentGateway.Api/README.md) and [DevFlow](../DevFlow/README.md). Runtime files, installed dependencies, and credentials remain local and are excluded from Git. When adding another MCP integration, give it a directory under `MCPs/` and add it to this index and the [root README](../README.md).
