import json
from typing import Any

from devflow.shared.errors import ClientError
from devflow.shared.git_client import FileChange
from devflow.shared.llm_client import Complexity, LlmResponse
from devflow.shared.tracker import Card


def slug_json(slug: str) -> str:
    return json.dumps({"slug": slug})


def message_json(commit_type: str, description: str) -> str:
    return json.dumps({"type": commit_type, "description": description})


class FakeTrackerClient:
    def __init__(self, card: Card | None = None, error: str | None = None) -> None:
        self.card = card
        self.error = error
        self.calls: list[int] = []

    def get_card(self, card_id: int) -> Card:
        self.calls.append(card_id)
        if self.error:
            raise ClientError(self.error)
        assert self.card is not None, "FakeTrackerClient needs a card or an error"
        return self.card


class FakeLlmClient:
    """Returns the responses in order; when they run out, repeats the last one."""

    def __init__(
        self,
        responses: list[str] | None = None,
        error: str | None = None,
        input_tokens: int = 10,
        output_tokens: int = 5,
        cost: float = 0.01,
    ) -> None:
        self.responses = responses or [slug_json("fix-login-error")]
        self.error = error
        self.input_tokens = input_tokens
        self.output_tokens = output_tokens
        self.cost = cost
        self.calls: list[tuple[str, Complexity | None, dict[str, Any] | None]] = []

    def complete(
        self,
        prompt: str,
        complexity: Complexity | None,
        json_schema: dict[str, Any] | None,
    ) -> LlmResponse:
        self.calls.append((prompt, complexity, json_schema))
        if self.error:
            raise ClientError(self.error)

        index = min(len(self.calls), len(self.responses)) - 1
        return LlmResponse(
            response=self.responses[index],
            model="fake-model",
            input_tokens=self.input_tokens,
            output_tokens=self.output_tokens,
            cost=self.cost,
        )


class FakeGitClient:
    def __init__(
        self,
        fetch_error: str | None = None,
        create_error: str | None = None,
        remote_url: str = "https://github.com/acme/my-repo.git",
        branch: str = "feature/52691-elearning-costs",
        changes: list[FileChange] | None = None,
        diff: str = "diff --git a/src/app.py b/src/app.py",
        branch_error: str | None = None,
        changes_error: str | None = None,
        diff_error: str | None = None,
    ) -> None:
        self.fetch_error = fetch_error
        self.create_error = create_error
        self.remote_url = remote_url
        self.branch = branch
        self.changes = [FileChange("src/app.py", "M")] if changes is None else changes
        self.diff = diff
        self.branch_error = branch_error
        self.changes_error = changes_error
        self.diff_error = diff_error
        self.calls: list[tuple[str, str, str]] = []
        self.remote_calls: list[str] = []
        self.diff_calls: list[list[str]] = []

    def get_remote_url(self, remote: str) -> str:
        self.remote_calls.append(remote)
        return self.remote_url

    def fetch(self, remote: str, branch: str) -> None:
        self.calls.append(("fetch", remote, branch))
        if self.fetch_error:
            raise ClientError(self.fetch_error)

    def create_branch(self, name: str, start_point: str) -> None:
        self.calls.append(("create_branch", name, start_point))
        if self.create_error:
            raise ClientError(self.create_error)

    def get_current_branch(self) -> str:
        if self.branch_error:
            raise ClientError(self.branch_error)
        return self.branch

    def get_changes(self) -> list[FileChange]:
        if self.changes_error:
            raise ClientError(self.changes_error)
        return self.changes

    def get_diff(self, paths: list[str]) -> str:
        self.diff_calls.append(paths)
        if self.diff_error:
            raise ClientError(self.diff_error)
        return self.diff


class FakeClipboardClient:
    def __init__(self, error: str | None = None) -> None:
        self.error = error
        self.copied: list[str] = []

    def copy(self, text: str) -> None:
        if self.error:
            raise ClientError(self.error)
        self.copied.append(text)
