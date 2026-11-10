import argparse
import re
import sys
from collections.abc import Callable, Sequence
from pathlib import Path
from typing import Any
from uuid import uuid4

from langgraph.checkpoint.memory import InMemorySaver
from langgraph.graph.state import CompiledStateGraph
from langgraph.types import Command

from devflow.commit_message.graph import build_graph
from devflow.commit_message.nodes import DEFAULT_MAX_LENGTH, DEFAULT_MIN_LENGTH
from devflow.shared.clipboard_client import WindowsClipboardClient
from devflow.shared.config import load_llm_settings
from devflow.shared.errors import ConfigError
from devflow.shared.git_client import SubprocessGitClient
from devflow.shared.llm_client import HttpLlmClient

ReviewPrompt = Callable[[dict[str, Any]], dict[str, Any]]
MAX_LISTED_FILES = 15


def parse_length_range(value: str) -> tuple[int, int]:
    """Parses `MIN-MAX` (for example `80-100`) into the target length of the description."""
    match = re.fullmatch(r"(\d+)-(\d+)", value.strip())
    if match is None:
        raise argparse.ArgumentTypeError(f"'{value}' is not a range like 80-100.")

    minimum, maximum = int(match.group(1)), int(match.group(2))
    if minimum < 1 or minimum > maximum:
        raise argparse.ArgumentTypeError(f"'{value}' is not a valid range (MIN <= MAX, MIN >= 1).")
    return minimum, maximum


def parse_args(argv: Sequence[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        prog="commit-message",
        description="Proposes a commit message from the pending git changes and copies it.",
    )
    parser.add_argument(
        "-l",
        "--length",
        type=parse_length_range,
        default=(DEFAULT_MIN_LENGTH, DEFAULT_MAX_LENGTH),
        metavar="MIN-MAX",
        help=(
            "Target length of the description in characters "
            f"(default: {DEFAULT_MIN_LENGTH}-{DEFAULT_MAX_LENGTH})"
        ),
    )
    return parser.parse_args(argv)


def edit_message(current: str) -> str:
    """Asks for the message with `current` already written, so it can be edited in place."""
    from prompt_toolkit import prompt  # imported here to keep the CLI startup fast

    return prompt("Commit message: ", default=current).strip()


def prompt_review(payload: dict[str, Any]) -> dict[str, Any]:
    """Shows the proposal and returns the user's decision as the resume value."""
    files = payload["changed_files"]
    print(f"\nBranch: {payload['branch_name'] or '(detached HEAD)'}")
    print(f"Changed files ({len(files)}):")
    for file in files[:MAX_LISTED_FILES]:
        print(f"  {file}")
    if len(files) > MAX_LISTED_FILES:
        print(f"  ... and {len(files) - MAX_LISTED_FILES} more")
    print(f"\nProposed message: {payload['message']}")

    while True:
        choice = input("[A]pprove, [E]dit or [R]eject: ").strip().lower()
        if choice in ("a", "approve"):
            return {"action": "approve"}
        if choice in ("e", "edit"):
            return {"action": "edit", "message": edit_message(payload["message"])}
        if choice in ("r", "reject"):
            return {"action": "reject", "feedback": input("Feedback (optional): ").strip()}
        print("Invalid option.")


def run(
    graph: CompiledStateGraph,
    min_length: int,
    max_length: int,
    review: ReviewPrompt = prompt_review,
) -> int:
    """Runs the graph and resolves each interrupt; returns the exit code."""
    config = {"configurable": {"thread_id": str(uuid4())}}
    result = graph.invoke({"min_length": min_length, "max_length": max_length}, config)

    while "__interrupt__" in result:
        decision = review(result["__interrupt__"][0].value)
        result = graph.invoke(Command(resume=decision), config)

    if error := result.get("error"):
        print(f"Error: {error}", file=sys.stderr)
        return 1

    print(f"\nCopied to the clipboard: {result['copied_message']}")
    print(
        f"LLM: {result.get('llm_input_tokens', 0)} input tokens, "
        f"{result.get('llm_output_tokens', 0)} output tokens, "
        f"cost {result.get('llm_cost', 0.0):.4f}"
    )
    return 0


def main(argv: Sequence[str] | None = None) -> int:
    args = parse_args(argv)
    min_length, max_length = args.length

    try:
        llm_settings = load_llm_settings()
    except ConfigError as exc:
        print(f"Configuration error: {exc}", file=sys.stderr)
        return 2

    graph = build_graph(
        llm=HttpLlmClient(llm_settings.api_url, llm_settings.api_key),
        git=SubprocessGitClient(cwd=Path.cwd()),
        clipboard=WindowsClipboardClient(),
        checkpointer=InMemorySaver(),
    )

    try:
        return run(graph, min_length, max_length)
    except (KeyboardInterrupt, EOFError):
        print("\nCancelled. Nothing was copied.", file=sys.stderr)
        return 130


if __name__ == "__main__":
    sys.exit(main())
