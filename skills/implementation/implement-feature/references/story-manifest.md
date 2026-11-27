# Story manifest

The manifest describes which repositories take part in the story. It lives inside
`implementation/state.json`. Build it during intake and ask the user to confirm it.

## Fields

| Field | Meaning |
| --- | --- |
| `story` | Identifier and title of the story. |
| `story_doc` | Path of the story document with the agreed plan. |
| `mode` | `parallel` or `sequential`. |
| `contract` | Path of `implementation/contract.md` or of an OpenAPI file. Empty in `sequential` mode until the backend is done. |
| `repos[].id` | Short name, for example `be`, `fe`, `iac`. |
| `repos[].role` | `backend`, `frontend` or `iac`. |
| `repos[].path` | Absolute path of the repository. |
| `repos[].scope` | Optional sub-paths that this role may edit. Used when IaC lives inside the backend repository. |
| `repos[].base_branch` | Branch to start from and to open the pull request against. |
| `repos[].host` | `github` or `azure-devops`. |
| `repos[].commands` | `build`, `unit_tests`, `style`, `integration_tests`, `e2e_tests`. Leave empty what does not exist. |
| `repos[].integration_local` | `allowed` or `ask`. Default `ask`. |
| `repos[].plan_steps` | Plan steps that belong to this repository. |

## Rules

- One writer per repository at a time. If two roles share a repository (backend and
  IaC), they take turns. Their scopes must not overlap.
- Several repositories can have the same role, for example two backends. Give each a
  different `id`. The contract says which one owns which part.
- A story without a frontend or without a backend is valid. Create only the repos that
  take part.
- Commands come from the repository files. If you did not read them there, ask.
- Do not guess a base branch. Read it from the repository or ask.

## Example

```json
{
  "story": { "id": "34", "title": "Manage recipes" },
  "story_doc": "docs/stories/34/README.md",
  "mode": "parallel",
  "contract": "docs/stories/34/implementation/contract.md",
  "repos": [
    {
      "id": "be",
      "role": "backend",
      "path": "C:/REPO/Personal/Happymeal/Happymeal-BE",
      "base_branch": "develop",
      "host": "github",
      "commands": {
        "build": "dotnet build",
        "unit_tests": "dotnet test --filter Category=Unit",
        "style": "dotnet format --verify-no-changes",
        "integration_tests": "dotnet test --filter Category=Integration"
      },
      "integration_local": "allowed",
      "plan_steps": ["1", "2", "3"]
    },
    {
      "id": "fe",
      "role": "frontend",
      "path": "C:/REPO/Personal/Happymeal/Happymeal-FE",
      "base_branch": "develop",
      "host": "github",
      "commands": {
        "build": "npm run build",
        "unit_tests": "npm test",
        "style": "npm run lint",
        "e2e_tests": "npx playwright test"
      },
      "integration_local": "allowed",
      "plan_steps": ["4", "5"]
    }
  ]
}
```

The example paths and commands only show the shape. Always read the real values.
