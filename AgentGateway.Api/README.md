# AgentGateway API

[Back to AI tools](../README.md)

A local .NET HTTP API that runs prompts through the Claude Code CLI. Clients send a prompt, an optional complexity level, and an optional JSON schema; the API selects a model and reasoning effort and returns the answer with token usage and reported cost. [DevFlow](../DevFlow/README.md) uses this API for its proposals.

## Requirements

- .NET 10 SDK compatible with [global.json](global.json), which requests `10.0.400` with `latestFeature` roll-forward.
- The `claude` executable available on the API process's PATH and already authenticated for the account you intend to use.
- An API key shared between the gateway and its callers.

Actual prompt requests invoke Claude Code and use that account's access and usage allowance. The setup and health-check commands below do not submit prompts.

## Run locally

From a PowerShell terminal in the repository root:

```powershell
cd AgentGateway.Api
dotnet restore AgentGateway.slnx
dotnet build AgentGateway.slnx --no-restore

# Replace this placeholder with your own local API key.
$env:Authentication__ApiKey = '<your-local-api-key>'
dotnet run --project src/AgentGateway.API --launch-profile http
```

The application listens at `http://localhost:5052`. Keep that terminal open and use another terminal for clients. Startup fails if the API key is empty. Do not place the real key in a versioned settings file.

In development you can use .NET user secrets instead of the environment variable, from this directory:

```powershell
dotnet user-secrets set 'Authentication:ApiKey' '<your-local-api-key>' --project src/AgentGateway.API
```

User secrets provide local configuration outside Git; they are not encrypted secret storage. An environment variable takes precedence if both are configured.

## Configuration

| Environment variable | Purpose | Default |
| --- | --- | --- |
| `Authentication__ApiKey` | Key required in the `X-Api-Key` request header. | Required; no built-in key. |
| `Claude__WorkingDirectory` | Working directory of the Claude Code subprocess. It is created if missing. | `workspace` under the application's base directory. |

Set configuration in the terminal before starting the API, or use the equivalent `Authentication:ApiKey` and `Claude:WorkingDirectory` keys in user secrets during development.

The executor loads Claude's project settings from its working directory, disables session persistence, and supplies an empty MCP configuration. Its allowed tool list is `Read,Edit,Grep,Bash(npm *)`; choose a working directory appropriate for the prompts you submit.

## Endpoints

| Method | Path | Authentication | Purpose |
| --- | --- | --- | --- |
| GET | `/health` | None | Checks that the web application is healthy; it does not test Claude authentication. |
| GET | `/scalar/v1` | None | Interactive API documentation. |
| GET | `/openapi/v1.json` | None | OpenAPI document. |
| POST | `/api/prompts` | `X-Api-Key` | Executes a prompt through Claude Code. |
| POST | `/api/llm` | `X-Api-Key` | Legacy alias; new clients should use `/api/prompts`. |

Check the running application without submitting a prompt:

```powershell
Invoke-WebRequest http://localhost:5052/health
```

Example prompt call, when you want to invoke Claude Code:

```powershell
$body = @{
    prompt = 'Suggest a short English branch slug for adding menu scheduling.'
    complexity = 'Low'
} | ConvertTo-Json

Invoke-RestMethod -Method Post `
    -Uri http://localhost:5052/api/prompts `
    -Headers @{ 'X-Api-Key' = '<your-local-api-key>' } `
    -ContentType 'application/json' `
    -Body $body
```

`prompt` must contain text. `complexity` defaults to `Medium`; accepted values are `Low`, `Medium`, `High`, `VeryHigh`, and `Max`. An optional `jsonSchema` JSON object is forwarded to Claude Code through `--json-schema`.

The response contains `response`, `model`, `inputTokens`, `outputTokens`, and `cost`. The model mapping is defined in [ModelProfile.cs](src/AgentGateway.Domain/ModelProfile.cs). Validation failures return `400`, missing or invalid API keys return `401`, and CLI execution or response parsing failures return `502`.

## Project layout

| Directory under `src/` | Responsibility |
| --- | --- |
| `AgentGateway.API` | HTTP endpoints, API-key authentication, and OpenAPI documentation. |
| `AgentGateway.Application` | Prompt execution use case and executor interface. |
| `AgentGateway.Domain` | Prompt validation, complexity levels, and model selection. |
| `AgentGateway.Infrastructure` | Claude Code subprocess execution and output parsing. |
| `AgentGateway.Common` | Results, errors, and validation helpers. |

## Use with DevFlow

Set `LLM_API_URL=http://localhost:5052/api/prompts` in DevFlow's local configuration and set `LLM_API_KEY` to the same value as this API's `Authentication__ApiKey`. Keep the gateway running while executing either DevFlow command. See the [DevFlow configuration guide](../DevFlow/README.md#configuration).
