import json
import re
from collections.abc import Callable
from pathlib import PurePosixPath
from typing import Any

from langgraph.types import interrupt

from devflow.commit_message.state import CommitMessageState
from devflow.shared.clipboard_client import ClipboardClient
from devflow.shared.errors import ClientError
from devflow.shared.git_client import FileChange, GitClient
from devflow.shared.llm_client import Complexity, LlmClient

COMMIT_TYPES = (
    "build",
    "chore",
    "ci",
    "docs",
    "feat",
    "fix",
    "perf",
    "refactor",
    "revert",
    "style",
    "test",
)
DEFAULT_MIN_LENGTH = 50
DEFAULT_MAX_LENGTH = 70
MAX_DIFF_LENGTH = 20_000
COMPLEXITY: Complexity = "Medium"
MESSAGE_JSON_SCHEMA: dict[str, Any] = {
    "type": "object",
    "properties": {
        "type": {"type": "string", "enum": list(COMMIT_TYPES)},
        "description": {"type": "string"},
    },
    "required": ["type", "description"],
    "additionalProperties": False,
}

# The story code is the 5-digit number right after the branch prefix: feature/52691-some-name.
STORY_CODE_PATTERN = re.compile(r"^[^/]+/(\d{5})(?!\d)")
GENERATED_DIRECTORIES = frozenset({"bin", "obj", "dist", "build", "node_modules", "__pycache__"})
GENERATED_SUFFIXES = (".tmp", ".pyc")
SUMMARY_FILE_PREFIX = "git-changes-summary"
LOCK_FILE_NAMES = frozenset({"package-lock.json", "packages.lock.json", "pnpm-lock.yaml"})

Node = Callable[[CommitMessageState], dict[str, Any]]


def extract_story_code(branch: str) -> str | None:
    match = STORY_CODE_PATTERN.match(branch)
    return match.group(1) if match else None


def is_noise(path: str) -> bool:
    """Hidden files, generated outputs and summary files never describe the real change."""
    parts = PurePosixPath(path).parts
    return (
        any(part.startswith(".") for part in parts)
        or any(part in GENERATED_DIRECTORIES for part in parts[:-1])
        or parts[-1].startswith(SUMMARY_FILE_PREFIX)
        or parts[-1].endswith(GENERATED_SUFFIXES)
    )


def is_lock_file(path: str) -> bool:
    name = PurePosixPath(path).name
    return name in LOCK_FILE_NAMES or name.endswith(".lock")


def select_relevant_changes(changes: list[FileChange]) -> list[FileChange]:
    """Drops the noise; lock files are kept only when they are the only meaningful change."""
    candidates = [change for change in changes if not is_noise(change.path)]
    source_changes = [change for change in candidates if not is_lock_file(change.path)]
    return source_changes or candidates


def truncate_diff(diff: str, max_length: int = MAX_DIFF_LENGTH) -> str:
    if len(diff) <= max_length:
        return diff
    return f"{diff[:max_length]}\n[diff truncated]"


def normalize_description(raw: str) -> str:
    """Returns the description in one line, with a capital first letter and a final period."""
    text = " ".join(raw.split()).rstrip(".").strip()
    if not text:
        return ""
    return f"{text[0].upper()}{text[1:]}."


def compose_message(commit_type: str, description: str, story_code: str | None) -> str:
    message = f"{commit_type}: {description}"
    return f"{message} story: #{story_code}" if story_code else message


def build_message_prompt(
    changed_files: list[str],
    diff: str,
    min_length: int,
    max_length: int,
    feedback: str | None,
    rejected_descriptions: list[str] | None = None,
) -> str:
    prompt = (
        "Write a git commit message for the pending changes below.\n"
        "Pick the type that best matches the dominant, user-visible intent of the change. "
        f"Allowed types: {', '.join(COMMIT_TYPES)}.\n"
        "Write the description in clear English at B2+ level. Start with a capital letter and "
        "do not add a final period. Do not include the type, a scope or a story code in it.\n"
        f"Target length of the description: {min_length} to {max_length} characters. "
        "It is a guideline: stay near the low end for small, focused changes and near the high "
        "end when several files or concerns are involved. Do not count characters.\n"
        "Describe the intent of the change, not the list of files.\n"
        "Changed files (git status code and path):\n" + "\n".join(changed_files)
    )
    if diff:
        prompt += f"\nDiff of the tracked files:\n{diff}"
    if feedback:
        prompt += (
            "\nA previous proposal was rejected by the user with this feedback. "
            f"Take it into account:\n{feedback}"
        )
    if rejected_descriptions:
        rejected = "\n".join(f"- {description}" for description in rejected_descriptions)
        prompt += (
            "\nThe user already rejected these descriptions. "
            f"Do not repeat them or return very similar ones:\n{rejected}"
        )
    return prompt


def make_read_branch(git: GitClient) -> Node:
    def read_branch(state: CommitMessageState) -> dict[str, Any]:
        try:
            branch = git.get_current_branch()
        except ClientError as exc:
            return {"error": str(exc)}
        return {"branch_name": branch, "story_code": extract_story_code(branch)}

    return read_branch


def make_read_changes(git: GitClient) -> Node:
    def read_changes(state: CommitMessageState) -> dict[str, Any]:
        try:
            changes = select_relevant_changes(git.get_changes())
            if not changes:
                return {"error": "There are no meaningful pending changes."}
            diff = git.get_diff([change.path for change in changes])
        except ClientError as exc:
            return {"error": str(exc)}

        return {
            "changed_files": [f"{change.status} {change.path}" for change in changes],
            "diff": truncate_diff(diff),
        }

    return read_changes


def make_propose_message(llm: LlmClient) -> Node:
    def propose_message(state: CommitMessageState) -> dict[str, Any]:
        prompt = build_message_prompt(
            state["changed_files"],
            state["diff"],
            state["min_length"],
            state["max_length"],
            state.get("feedback"),
            state.get("rejected_descriptions"),
        )
        try:
            result = llm.complete(prompt, COMPLEXITY, MESSAGE_JSON_SCHEMA)
        except ClientError as exc:
            return {"error": str(exc)}

        try:
            data = json.loads(result.response)
            commit_type = str(data["type"]).strip().lower()
            description = normalize_description(str(data["description"]))
        except (ValueError, KeyError, TypeError, AttributeError):
            return {"error": "The LLM did not return a valid commit message."}
        if commit_type not in COMMIT_TYPES:
            return {"error": f"The LLM returned an invalid commit type: '{commit_type}'."}
        if not description:
            return {"error": "The LLM returned an empty description."}

        return {
            "commit_type": commit_type,
            "description": description,
            "message": compose_message(commit_type, description, state.get("story_code")),
            "llm_input_tokens": state.get("llm_input_tokens", 0) + result.input_tokens,
            "llm_output_tokens": state.get("llm_output_tokens", 0) + result.output_tokens,
            "llm_cost": state.get("llm_cost", 0.0) + result.cost,
        }

    return propose_message


def human_review(state: CommitMessageState) -> dict[str, Any]:
    # This node reruns from the start on resume: no side effects before the interrupt.
    decision = interrupt(
        {
            "branch_name": state["branch_name"],
            "changed_files": state["changed_files"],
            "message": state["message"],
        }
    )

    action = decision.get("action")
    if action == "approve":
        return {"review_action": "approve"}
    if action == "edit":
        edited_message = str(decision.get("message", "")).strip()
        if not edited_message:
            return {"error": "The edited commit message is empty."}
        return {"review_action": "edit", "message": edited_message}
    if action == "reject":
        return {
            "review_action": "reject",
            "feedback": decision.get("feedback") or None,
            "rejected_descriptions": [
                *state.get("rejected_descriptions", []),
                state["description"],
            ],
        }
    return {"error": f"Unknown review action: {action!r}."}


def make_copy_message(clipboard: ClipboardClient) -> Node:
    def copy_message(state: CommitMessageState) -> dict[str, Any]:
        message = state["message"]
        try:
            clipboard.copy(message)
        except ClientError as exc:
            # The message is part of the error so the user does not lose it.
            return {"error": f"{exc} The approved message was: {message}"}
        return {"copied_message": message}

    return copy_message
