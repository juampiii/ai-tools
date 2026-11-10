---
name: langgraph-architecture
description: Architecture rules for the DevFlow LangGraph graphs — state design, nodes, conditional edges, LLM usage, human interrupts (interrupt/Command), checkpointer, errors and dependency injection. Always use it when creating, changing or reviewing a graph, a node, the state or an external client (Azure DevOps, LLM, git), or when start-branch, finish-branch or any new graph is discussed.
---

# Graph architecture in DevFlow

## General principle: workflow, not agent

DevFlow graphs are **workflows**: the code defines the steps and their order. Agents where the LLM decides which tools to call are not used. If a step can be done with deterministic code, it is done with code.

## State

- Each graph defines its state in `state.py` as a `TypedDict`.
- The state holds only data: input, intermediate results and final result. No clients, connections or functions.
- It includes an `error: str | None` field. Any node that fails writes a clear message for the user there.
- Fields are named in English and in `snake_case` (`card_id`, `card_title`, `card_type`, `branch_prefix`, `branch_name`).

## Nodes

- A node is a function `(state) -> dict` that reads from the state and returns **only the fields it updates**. It does not return the full state and does not mutate it.
- A node knows nothing about the graph: it does not decide the next step and does not know other nodes.
- A node does not interact with the console. User interaction is done exclusively through `interrupt()`.
- If an external operation fails, the node returns `{"error": "..."}` instead of raising an exception, and the routing decides what to do.

## External dependencies (dependency injection)

- Each external system has a client in `devflow/shared/`: `ado_client.py`, `github_client.py`, `llm_client.py`, `git_client.py`. Each client is defined with a `Protocol` (the interface) and a real implementation. Work trackers (Azure DevOps, GitHub) share one `TrackerClient` Protocol and the `Card` value, both in `tracker.py`; graphs depend only on `TrackerClient`.
- Nodes **do not import concrete clients or the global configuration**. The graph is built with a factory function that receives the dependencies:

  ```python
  def build_graph(
      tracker: TrackerClient,
      llm: LlmClient,
      git: GitClient,
      checkpointer: BaseCheckpointSaver,
      base_branch: str,
  ) -> CompiledStateGraph:
      ...
  ```

  Nodes are created inside the factory (closures) or as functions that receive the client and are wrapped with `functools.partial`. It is the equivalent of constructor injection in .NET and it is what allows testing with fakes.
- The real composition (real clients + config) happens only in the CLI entry point.

## Edges and routing

- Every flow decision goes in a **conditional edge** (`add_conditional_edges`) with a small, pure routing function that reads the state and returns the name of the next node (or `END`).
- After any node that can fail, the routing checks `error` and, if it is set, goes to `END`.
- Routing functions have no side effects and do not call clients.

## LLM usage

- The LLM is used only where language has to be interpreted or generated. In `start-branch`, only to generate the slug of the branch name.
- It is consumed through `LlmClient`, which calls our own API `POST {LLM_API_URL}` with the body `{"prompt": str, "complexity": "Low"|"Medium"|"High"|"VeryHigh"|"Max"|null, "jsonSchema": object|null}` and receives `{"response", "model", "inputTokens", "outputTokens", "cost"}`. Error codes: 400 (invalid request) and 502 (CLI failure).
- Always use `jsonSchema` to get structured answers; never parse free text.
- Use the lowest `complexity` that is enough for the task (`Low` for a slug).
- Store the usage (tokens and cost) in the state to show it at the end of the run.
- The LLM never decides values that can be computed: the branch prefix and the card id are computed with code and concatenated outside the LLM. Always normalize the LLM output (lowercase, kebab-case, maximum length) before using it.

## Human interrupts

- Confirmations are done with `interrupt(payload)` from `langgraph.types` inside a dedicated node (`human_review`). The payload contains what the CLI must show.
- The CLI resumes with `Command(resume=value)` using the same `thread_id`.
- The resume value is an explicit structure, not a free string: `{"action": "approve"}`, `{"action": "edit", "branch_name": "..."}` or `{"action": "reject", "feedback": "..."}`.
- A rejection with feedback goes back to the node that proposes, which receives the feedback through the state.
- The node that contains `interrupt()` **reruns from the start** on resume: do not put side effects before the `interrupt()` in that node.
- Every graph with interrupts is compiled with a checkpointer. Locally, `InMemorySaver` is used.

## Side effects

- Operations that change something (create a branch, change a card) go in dedicated nodes, at the end and only after the human confirmation.
- Before a side effect, the state must already have all the data needed; the node does not recompute anything.

## Graph layout

```
devflow/<graph>/
├── __init__.py
├── state.py     # state TypedDict
├── nodes.py     # node functions
├── routing.py   # routing functions
├── graph.py     # build_graph(...): nodes + edges + compile
└── cli.py       # composition with real clients, invoke/interrupt/resume loop, console output
```

## start-branch (v2)

Flow: `read_card` → `resolve_prefix` → (unsupported type → `END` with error) → `git_fetch` → `propose_name` → `human_review` → (rejection → `propose_name`) → `create_branch` → `END`.

- Input: the card id as a command argument (`start-branch 12345`). It runs on the git repository of the current directory.
- Tracker: `-t` / `--tracker` with `ado` or `github`. Without it, `DEFAULT_TRACKER` is used, or `ado`. Only the variables of the selected tracker are required.
- GitHub: the card is an issue (pull requests are rejected). Owner and repository are deduced from the `origin` remote in the CLI composition (`create_tracker`), never inside the nodes. A remote that is not `github.com` ends with an error.
- Card types: the tracker client returns the card type; GitHub issues are `Bug` when they have the `bug` label and `Issue` otherwise.
- Prefixes: `{"Bug": "bugfix/", "User Story": "feature/", "Product Backlog Item": "feature/", "Issue": "feature/"}`. Any other type ends with an error.
- Branch name: `{prefix}{card_id}-{slug}`. The LLM generates the slug: short, in English, kebab-case.
- The branch is created from `origin/{BASE_BRANCH}`.
- Out of scope: several repositories, checking whether the branch already exists, checking the working tree, changing the card in the tracker, reading the GitHub Project board (draft items), GitHub Enterprise, a card hosted in a different place than the code repository.

## commit-message

Flow: `read_branch` → `read_changes` → `propose_message` → `human_review` → (rejection → `propose_message`) → `copy_message` → `END`. Any node that fails ends the graph with `error`.

- Input: `--length MIN-MAX` (default 50-70), the target length of the description. It is a guideline for the LLM; the code does not verify it. It runs on the git repository of the current directory.
- It needs no tracker: the CLI reads only `LLM_API_URL` with `load_llm_api_url`.
- Story code: computed with code from the branch name (`feature/52691-name` → `52691`) and appended outside the LLM. Without a code, no suffix.
- Changes: `git status` (staged, unstaged, untracked) filtered with code. Noise is dropped (hidden paths, `bin/`, `obj/`, `git-changes-summary*`, temporary files); lock files are kept only when they are the only meaningful change. The diff (`git diff HEAD`) is requested only for the kept paths and truncated to `MAX_DIFF_LENGTH`.
- LLM: returns `{"type", "description"}` with `jsonSchema` and `Medium` complexity. The type must be one of `COMMIT_TYPES`. The description is normalized (one line, capital letter, final period). The final message is `<type>: <Description>. story: #<code>`.
- The only side effect is `copy_message`, after the confirmation, through `ClipboardClient` (`clip` on Windows). It does not run `git commit`. If the clipboard fails, the error includes the approved message.
- Out of scope: committing, the `task: #...` code, ranges other than the target length, several repositories, clipboards other than Windows.
