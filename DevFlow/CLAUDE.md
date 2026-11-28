# DevFlow

Personal development-workflow automation tools, built as LangGraph graphs in Python.

## Purpose

Each tool is a LangGraph graph that is invoked from the terminal. The first one is `start-branch`: it reads a card from Azure DevOps (default) or a GitHub issue, resolves the branch prefix from the card type or labels, proposes a branch name, asks the user for confirmation and creates the branch from `origin/<BASE_BRANCH>` (`develop` by default). The second one is `commit-message`: it reads the pending git changes, proposes a conventional-commit message, asks the user for confirmation and copies it to the clipboard.

The project also has a learning goal: the author comes from .NET/C# and is learning Python and LangGraph. When you explain decisions, use .NET analogies if they help.

## Project rules

Before writing or changing code, read the project skills:

- `.claude/skills/python-conventions/SKILL.md`: style, tools (`uv`, `ruff`), typing and project structure.
- `.claude/skills/langgraph-architecture/SKILL.md`: how state, nodes, edges, interrupts and external dependencies are designed.
- `.claude/skills/testing/SKILL.md`: how nodes and graphs are tested.

## Structure

```
DevFlow/
├── .claude/skills/
├── CLAUDE.md
├── pyproject.toml
├── .env.example
├── src/devflow/
│   ├── shared/            # config, errors, tracker protocol and clients (ADO, GitHub, LLM, git, clipboard)
│   ├── start_branch/      # state, nodes, graph, CLI entry point
│   └── commit_message/    # state, nodes, graph, CLI entry point
└── tests/
```

## Commands

- Install dependencies: `uv sync`
- Run: `uv run start-branch <card-id>`
- Run: `uv run commit-message [--length MIN-MAX]`
- Tests: `uv run pytest`
- Lint and format: `uv run ruff check --fix` and `uv run ruff format`

Before considering a task done, run tests, lint and format, and make sure they pass.

## Environment

- Development on Windows. Use `pathlib` paths, never strings joined with `/` or `\`.
- The LLM is consumed through our own HTTP API (`POST /api/prompts`) that wraps the Claude Code CLI. Its URL comes from the `LLM_API_URL` variable and its API key from `LLM_API_KEY` (sent in the `X-Api-Key` header).
- All configuration comes from environment variables (a local `.env` file, never versioned). `.env.example` documents all the variables without secret values.
