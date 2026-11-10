---
name: testing
description: How DevFlow is tested — pytest, fakes for the external clients (Azure DevOps, LLM, git), isolated node tests, routing function tests and full graph tests including interrupt and resume. Always use it when writing or changing code in src/devflow, adding a node or graph, or when asked to write, review or fix tests.
---

# Testing in DevFlow

## Tools

- `pytest` as the framework (dev dependency with `uv add --dev pytest`).
- Run with: `uv run pytest`.
- Hand-written **fakes** that implement the clients' `Protocol` are preferred over mocking libraries.

## General rules

- Tests **never** call real systems: not Azure DevOps, not GitHub, not the LLM API, not git on a real repository.
- Each client in `devflow/shared/` has a fake in `tests/fakes.py` that implements its `Protocol`, is configurable from the test (what it returns, whether it fails) and records the calls it receives so they can be verified.
- Shared fixtures (already built fakes, a graph compiled with fakes) go in `tests/conftest.py`.
- Descriptive test names in English: `test_resolve_prefix_returns_bugfix_for_bug`.
- Arrange / Act / Assert structure, one behavior per test.
- The structure of `tests/` mirrors that of `src/devflow/` (`tests/start_branch/test_nodes.py`, etc.).

## What is tested at each level

### Routing functions
They are pure functions: test them by passing a state and checking the name of the next node. They must cover all branches, including the error one.

### Nodes
- Each node is tested in isolation, with an input state and the fakes it needs, checking the dict it returns.
- Cover the happy path and the client failures (the node must return `error`, not raise).
- In `propose_name`, check that the prompt sent to the LLM fake includes the title and, when there is one, the feedback from the previous rejection; that the prefix and the card id are set by the code, not by the LLM; and that the LLM output is normalized.

### Real clients
- Their translation logic (parsing the ADO or LLM API response, building the git arguments) is tested without network or processes: with `httpx.MockTransport` for HTTP and by checking the argument list that would be passed to `subprocess.run`.

### Full graph
- It is built with `build_graph(...)` passing fakes and an `InMemorySaver`.
- It is invoked with its own `thread_id` per test.
- For flows with an interrupt: first `invoke` up to the pause, check the interrupt payload and resume with `Command(resume=...)` using the same `thread_id`.
- Minimum `start-branch` scenarios:
  - Approved Bug: a `bugfix/...` branch is created from `origin/develop`.
  - Approved User Story: a `feature/...` branch is created.
  - Unsupported type: ends with an error and git is not called.
  - Card not found: ends with an error and git is not called.
  - LLM failure (502): ends with an error and the branch is not created.
  - Rejection with feedback and later approval: the LLM is called twice, the second time with the feedback.
  - Manual edit of the name: the branch is created with the edited name.
- Also verify what must **not** happen: no side effect (creating a branch) before the approval.

## Before finishing a task

`uv run pytest`, `uv run ruff check` and `uv run ruff format --check` must pass.
