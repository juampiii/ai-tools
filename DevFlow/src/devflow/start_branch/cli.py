import argparse
import sys
from collections.abc import Callable, Sequence
from pathlib import Path
from typing import Any
from uuid import uuid4

from langgraph.checkpoint.memory import InMemorySaver
from langgraph.graph.state import CompiledStateGraph
from langgraph.types import Command

from devflow.shared.ado_client import HttpAdoClient
from devflow.shared.config import SUPPORTED_TRACKERS, Settings, load_settings
from devflow.shared.errors import ClientError, ConfigError
from devflow.shared.git_client import GitClient, SubprocessGitClient
from devflow.shared.github_client import HttpGitHubClient, parse_github_remote
from devflow.shared.llm_client import HttpLlmClient
from devflow.shared.tracker import TrackerClient
from devflow.start_branch.graph import build_graph
from devflow.start_branch.nodes import REMOTE

ReviewPrompt = Callable[[dict[str, Any]], dict[str, Any]]


def parse_args(argv: Sequence[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        prog="start-branch",
        description="Creates a git branch from a card of a work tracker.",
    )
    parser.add_argument(
        "card_id", type=int, help="Card id (Azure DevOps work item or GitHub issue number)"
    )
    parser.add_argument(
        "-t",
        "--tracker",
        choices=SUPPORTED_TRACKERS,
        default=None,
        help="Work tracker to read the card from (default: DEFAULT_TRACKER, or ado)",
    )
    return parser.parse_args(argv)


def create_tracker(settings: Settings, git: GitClient) -> TrackerClient:
    """Builds the client of the selected tracker; GitHub deduces owner/repo from `origin`."""
    if settings.tracker == "github":
        repo = parse_github_remote(git.get_remote_url(REMOTE))
        return HttpGitHubClient(repo, settings.github_token or "")

    ado = settings.ado
    if ado is None:
        raise ConfigError("Azure DevOps settings are missing.")
    return HttpAdoClient(ado.organization, ado.project, ado.pat)


def edit_branch_name(current: str) -> str:
    """Asks for the branch name with `current` already written, so it can be edited in place."""
    from prompt_toolkit import prompt  # imported here to keep the CLI startup fast

    return prompt("Branch name: ", default=current).strip()


def prompt_review(payload: dict[str, Any]) -> dict[str, Any]:
    """Shows the proposal and returns the user's decision as the resume value."""
    print(f"\nCard: {payload['card_title']}")
    print(f"Proposed branch: {payload['branch_name']}")

    while True:
        choice = input("[A]pprove, [E]dit or [R]eject: ").strip().lower()
        if choice in ("a", "approve"):
            return {"action": "approve"}
        if choice in ("e", "edit"):
            return {"action": "edit", "branch_name": edit_branch_name(payload["branch_name"])}
        if choice in ("r", "reject"):
            return {"action": "reject", "feedback": input("Feedback (optional): ").strip()}
        print("Invalid option.")


def run(graph: CompiledStateGraph, card_id: int, review: ReviewPrompt = prompt_review) -> int:
    """Runs the graph and resolves each interrupt; returns the exit code."""
    config = {"configurable": {"thread_id": str(uuid4())}}
    result = graph.invoke({"card_id": card_id}, config)

    while "__interrupt__" in result:
        decision = review(result["__interrupt__"][0].value)
        result = graph.invoke(Command(resume=decision), config)

    if error := result.get("error"):
        print(f"Error: {error}", file=sys.stderr)
        return 1

    print(f"\nCreated branch: {result['created_branch']}")
    print(
        f"LLM: {result.get('llm_input_tokens', 0)} input tokens, "
        f"{result.get('llm_output_tokens', 0)} output tokens, "
        f"cost {result.get('llm_cost', 0.0):.4f}"
    )
    return 0


def main(argv: Sequence[str] | None = None) -> int:
    args = parse_args(argv)

    try:
        settings = load_settings(tracker=args.tracker)
    except ConfigError as exc:
        print(f"Configuration error: {exc}", file=sys.stderr)
        return 2

    git = SubprocessGitClient(cwd=Path.cwd())
    try:
        tracker = create_tracker(settings, git)
    except ConfigError as exc:
        print(f"Configuration error: {exc}", file=sys.stderr)
        return 2
    except ClientError as exc:
        print(f"Error: {exc}", file=sys.stderr)
        return 1

    graph = build_graph(
        tracker=tracker,
        llm=HttpLlmClient(settings.llm.api_url, settings.llm.api_key),
        git=git,
        checkpointer=InMemorySaver(),
        base_branch=settings.base_branch,
    )

    try:
        return run(graph, args.card_id)
    except (KeyboardInterrupt, EOFError):
        print("\nCancelled. No branch was created.", file=sys.stderr)
        return 130


if __name__ == "__main__":
    sys.exit(main())
