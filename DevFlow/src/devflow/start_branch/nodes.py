import json
import re
from collections.abc import Callable
from typing import Any

from langgraph.types import interrupt

from devflow.shared.errors import ClientError
from devflow.shared.git_client import GitClient
from devflow.shared.llm_client import LlmClient
from devflow.shared.tracker import TrackerClient
from devflow.start_branch.state import StartBranchState

BRANCH_PREFIXES = {
    "Bug": "bugfix/",
    "Service Request": "bugfix/",
    "Freshdesk Bug": "bugfix/",
    "User Story": "feature/",
    "Product Backlog Item": "feature/",
    "Issue": "feature/",
}
REMOTE = "origin"
MAX_SLUG_LENGTH = 50
SLUG_JSON_SCHEMA: dict[str, Any] = {
    "type": "object",
    "properties": {"slug": {"type": "string"}},
    "required": ["slug"],
    "additionalProperties": False,
}

Node = Callable[[StartBranchState], dict[str, Any]]


def normalize_slug(raw: str, max_length: int = MAX_SLUG_LENGTH) -> str:
    """Returns the slug in lowercase kebab-case with a limited length (cut on a word boundary)."""
    slug = re.sub(r"[^a-z0-9]+", "-", raw.lower()).strip("-")
    if len(slug) <= max_length:
        return slug

    truncated = slug[:max_length]
    if slug[max_length] != "-" and "-" in truncated:
        truncated = truncated.rsplit("-", 1)[0]
    return truncated.strip("-")


def build_slug_prompt(
    title: str, feedback: str | None, rejected_slugs: list[str] | None = None
) -> str:
    prompt = (
        "Generate a short slug for a git branch name from the work item title below.\n"
        "Rules: English, kebab-case (lowercase words separated by hyphens), 2 to 5 words. "
        "Do not include any id or prefix. Translate the title to English if needed.\n"
        f"Title: {title}"
    )
    if feedback:
        prompt += (
            "\nA previous proposal was rejected by the user with this feedback. "
            f"Take it into account:\n{feedback}"
        )
    if rejected_slugs:
        rejected = "\n".join(f"- {slug}" for slug in rejected_slugs)
        prompt += (
            "\nThe user already rejected these slugs. "
            f"Do not repeat them or return very similar ones:\n{rejected}"
        )
    return prompt


def make_read_card(tracker: TrackerClient) -> Node:
    def read_card(state: StartBranchState) -> dict[str, Any]:
        try:
            card = tracker.get_card(state["card_id"])
        except ClientError as exc:
            return {"error": str(exc)}
        return {"card_title": card.title, "card_type": card.type}

    return read_card


def resolve_prefix(state: StartBranchState) -> dict[str, Any]:
    card_type = state["card_type"]
    prefix = BRANCH_PREFIXES.get(card_type)
    if prefix is None:
        supported = ", ".join(BRANCH_PREFIXES)
        return {"error": f"Unsupported card type: '{card_type}'. Supported: {supported}."}
    return {"branch_prefix": prefix}


def make_git_fetch(git: GitClient, base_branch: str) -> Node:
    def git_fetch(state: StartBranchState) -> dict[str, Any]:
        try:
            git.fetch(REMOTE, base_branch)
        except ClientError as exc:
            return {"error": str(exc)}
        return {}

    return git_fetch


def make_propose_name(llm: LlmClient) -> Node:
    def propose_name(state: StartBranchState) -> dict[str, Any]:
        prompt = build_slug_prompt(
            state["card_title"], state.get("feedback"), state.get("rejected_slugs")
        )
        try:
            result = llm.complete(prompt, "Low", SLUG_JSON_SCHEMA)
        except ClientError as exc:
            return {"error": str(exc)}

        try:
            slug = normalize_slug(json.loads(result.response)["slug"])
        except (ValueError, KeyError, TypeError, AttributeError):
            return {"error": "The LLM did not return a valid slug."}
        if not slug:
            return {"error": "The LLM returned an empty slug."}

        return {
            "branch_name": f"{state['branch_prefix']}{state['card_id']}-{slug}",
            "branch_slug": slug,
            "llm_input_tokens": state.get("llm_input_tokens", 0) + result.input_tokens,
            "llm_output_tokens": state.get("llm_output_tokens", 0) + result.output_tokens,
            "llm_cost": state.get("llm_cost", 0.0) + result.cost,
        }

    return propose_name


def human_review(state: StartBranchState) -> dict[str, Any]:
    # This node reruns from the start on resume: no side effects before the interrupt.
    decision = interrupt({"card_title": state["card_title"], "branch_name": state["branch_name"]})

    action = decision.get("action")
    if action == "approve":
        return {"review_action": "approve"}
    if action == "edit":
        edited_name = str(decision.get("branch_name", "")).strip()
        if not edited_name:
            return {"error": "The edited branch name is empty."}
        return {"review_action": "edit", "branch_name": edited_name}
    if action == "reject":
        return {
            "review_action": "reject",
            "feedback": decision.get("feedback") or None,
            "rejected_slugs": [state["branch_slug"]],
        }
    return {"error": f"Unknown review action: {action!r}."}


def make_create_branch(git: GitClient, base_branch: str) -> Node:
    def create_branch(state: StartBranchState) -> dict[str, Any]:
        branch_name = state["branch_name"]
        try:
            git.create_branch(branch_name, f"{REMOTE}/{base_branch}")
        except ClientError as exc:
            return {"error": str(exc)}
        return {"created_branch": branch_name}

    return create_branch
