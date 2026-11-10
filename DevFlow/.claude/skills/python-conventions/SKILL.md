---
name: python-conventions
description: Python conventions for the DevFlow project — PEP 8 style, uv, ruff, type hints, src/ layout, configuration and external process handling. Always use it when creating, changing or reviewing any .py file, pyproject.toml or project configuration, even if the change looks small.
---

# Python conventions in DevFlow

The project author comes from C#. These rules avoid the typical mistakes of that transition and keep the code idiomatic.

## Tools

- **`uv`** manages Python, the virtual environment and the dependencies. Do not use `pip install` directly and do not create virtual environments by hand. Add dependencies with `uv add <package>`; dev dependencies with `uv add --dev <package>`.
- **`ruff`** is the linter and the formatter. Configure it in `pyproject.toml`. The code must pass `ruff check` and `ruff format` with no changes.
- **`pyproject.toml`** is the only source of project configuration: metadata, dependencies, commands (`[project.scripts]`) and tool settings. Do not create `setup.py`, `requirements.txt` or `setup.cfg`.
- Minimum Python version: 3.12.

## Structure

- `src/` layout: the code lives in `src/devflow/`. Tests live in `tests/`, outside the package.
- Each graph is a subpackage of `devflow` (`devflow/start_branch/`). Anything used by several graphs goes in `devflow/shared/`; it is never duplicated.
- Command names use hyphens (`start-branch`) and are declared in `[project.scripts]`; modules and packages use underscores (`start_branch`). Python does not allow hyphens in module names.
- Every package has its `__init__.py`.

## Style (PEP 8)

- `snake_case` for functions, variables, modules and packages. `PascalCase` only for classes. `UPPER_SNAKE_CASE` for module constants.
- Identifier names, comments and docstrings are in English (`read_card`, `resolve_prefix`).
- Absolute imports (`from devflow.shared.config import settings`), grouped as: standard library, third party, project. `ruff` sorts them.
- Short functions with a single responsibility. Prefer functions to classes when there is no state to encapsulate; do not create classes just to group functions (in Python that is a module).

## Typing

- Type hints are mandatory on all public signatures and on state fields.
- Use the modern syntax: `list[str]`, `dict[str, int]`, `str | None` (not `List`, `Dict`, `Optional`).
- For data structures without behavior, use `TypedDict` (LangGraph state) or `@dataclass(frozen=True)` (domain values, client responses).
- Do not use `Any` except at the boundary with external data that has no schema, and convert it to a concrete type as soon as possible.

## Configuration

- All configuration is read from environment variables in a single module, `devflow/shared/config.py`, loading `.env` with `python-dotenv`.
- The module exposes a typed configuration object (dataclass). The rest of the code receives that object or the values it needs; it never calls `os.environ` directly.
- Values with a reasonable default (for example `LLM_API_URL=http://localhost:5052/api/prompts`, `BASE_BRANCH=develop`) have one. Secrets (`ADO_PAT`) have no default and their absence produces a clear error at startup.
- `.env` is in `.gitignore`. `.env.example` lists all the variables with example values, without secrets.

## External processes and HTTP

- External commands (git) use `subprocess.run` with an **argument list**, `check=False`, `capture_output=True`, `text=True`. Never `shell=True` and never commands built by concatenating strings.
- Interpret the `returncode` and return a typed result; do not let a git failure become an unhandled exception far from its origin.
- HTTP uses `httpx`, always with an explicit timeout. Keep in mind that the LLM API starts the Claude Code CLI on every call: use a generous timeout (60 s or more).
- Paths use `pathlib.Path`.

## Errors

- Do not use a generic `except Exception:` except at an explicit boundary (the CLI entry point) and never to silence errors.
- Catch specific exceptions (`httpx.HTTPError`, `httpx.TimeoutException`) close to their origin and convert them into typed results or clear messages.

## Console output

- User interaction (showing proposals, asking for confirmation) lives only in the CLI module of each graph, never inside the nodes.
