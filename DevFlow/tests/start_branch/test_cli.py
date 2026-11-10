from typing import Any

import pytest

from devflow.shared.ado_client import HttpAdoClient
from devflow.shared.config import AdoSettings, LlmSettings, Settings
from devflow.shared.errors import ClientError, ConfigError
from devflow.shared.github_client import HttpGitHubClient
from devflow.start_branch import cli
from devflow.start_branch.cli import (
    create_tracker,
    edit_branch_name,
    parse_args,
    prompt_review,
    run,
)
from tests.fakes import FakeGitClient

LLM_SETTINGS = LlmSettings(api_url="http://llm.test", api_key="llm-key")


def ado_settings() -> Settings:
    return Settings(
        tracker="ado",
        llm=LLM_SETTINGS,
        base_branch="develop",
        ado=AdoSettings(organization="org", project="proj", pat="secret"),
    )


def github_settings() -> Settings:
    return Settings(
        tracker="github",
        llm=LLM_SETTINGS,
        base_branch="develop",
        github_token="gh-secret",
    )


def test_parse_args_tracker_is_none_when_not_given():
    assert parse_args(["123"]).tracker is None


@pytest.mark.parametrize("flag", ["-t", "--tracker"])
def test_parse_args_accepts_the_short_and_long_tracker_flags(flag: str):
    args = parse_args(["123", flag, "github"])

    assert args.card_id == 123
    assert args.tracker == "github"


def test_parse_args_rejects_an_unknown_tracker(capsys):
    with pytest.raises(SystemExit):
        parse_args(["123", "--tracker", "jira"])

    assert "jira" in capsys.readouterr().err


def test_create_tracker_returns_the_ado_client_for_ado():
    git = FakeGitClient()

    tracker = create_tracker(ado_settings(), git)

    assert isinstance(tracker, HttpAdoClient)
    assert git.remote_calls == []


def test_create_tracker_deduces_the_github_repo_from_the_origin_remote():
    git = FakeGitClient(remote_url="git@github.com:acme/my-repo.git")

    tracker = create_tracker(github_settings(), git)

    assert isinstance(tracker, HttpGitHubClient)
    assert git.remote_calls == ["origin"]


def test_create_tracker_fails_when_the_origin_remote_is_not_github():
    git = FakeGitClient(remote_url="https://dev.azure.com/org/project/_git/repo")

    with pytest.raises(ClientError, match="not a github.com repository"):
        create_tracker(github_settings(), git)


def test_create_tracker_fails_when_ado_settings_are_missing():
    settings = Settings(tracker="ado", llm=LLM_SETTINGS, base_branch="develop")

    with pytest.raises(ConfigError):
        create_tracker(settings, FakeGitClient())


def test_run_resolves_the_interrupt_and_prints_branch_and_usage(graph, git, capsys):
    shown: list[dict[str, Any]] = []

    def review(payload: dict[str, Any]) -> dict[str, Any]:
        shown.append(payload)
        return {"action": "approve"}

    exit_code = run(graph, 12345, review)

    output = capsys.readouterr().out
    assert exit_code == 0
    assert shown[0]["branch_name"] == "bugfix/12345-fix-login-error"
    assert "Created branch: bugfix/12345-fix-login-error" in output
    assert "10 input tokens" in output
    assert "5 output tokens" in output


def test_run_prints_the_error_and_returns_failure_code(graph, tracker, capsys):
    tracker.error = "Card 12345 does not exist in Azure DevOps."

    exit_code = run(graph, 12345, lambda payload: {"action": "approve"})

    assert exit_code == 1
    assert "Card 12345 does not exist" in capsys.readouterr().err


# --- prompt_review --------------------------------------------------------------------------

REVIEW_PAYLOAD = {"card_title": "Fix login", "branch_name": "bugfix/1-fix-login"}


def answer_with(monkeypatch: pytest.MonkeyPatch, *answers: str) -> list[str]:
    asked: list[str] = []
    remaining = list(answers)

    def fake_input(prompt: str = "") -> str:
        asked.append(prompt)
        return remaining.pop(0)

    monkeypatch.setattr("builtins.input", fake_input)
    return asked


@pytest.mark.parametrize("answer", ["a", "A", "approve"])
def test_prompt_review_approves(monkeypatch: pytest.MonkeyPatch, answer: str):
    answer_with(monkeypatch, answer)

    assert prompt_review(REVIEW_PAYLOAD) == {"action": "approve"}


def test_prompt_review_edit_starts_from_the_proposed_name(monkeypatch: pytest.MonkeyPatch):
    answer_with(monkeypatch, "e")
    received: list[str] = []

    def fake_edit(current: str) -> str:
        received.append(current)
        return "bugfix/1-edited"

    monkeypatch.setattr(cli, "edit_branch_name", fake_edit)

    result = prompt_review(REVIEW_PAYLOAD)

    assert received == ["bugfix/1-fix-login"]
    assert result == {"action": "edit", "branch_name": "bugfix/1-edited"}


def test_prompt_review_reject_returns_the_feedback(monkeypatch: pytest.MonkeyPatch):
    answer_with(monkeypatch, "r", "too long")

    assert prompt_review(REVIEW_PAYLOAD) == {"action": "reject", "feedback": "too long"}


def test_prompt_review_asks_again_after_an_invalid_option(monkeypatch: pytest.MonkeyPatch, capsys):
    asked = answer_with(monkeypatch, "x", "a")

    result = prompt_review(REVIEW_PAYLOAD)

    assert result == {"action": "approve"}
    assert len(asked) == 2
    assert "Invalid option" in capsys.readouterr().out


# --- edit_branch_name -----------------------------------------------------------------------


def test_edit_branch_name_prefills_the_current_name_and_trims_the_result(
    monkeypatch: pytest.MonkeyPatch,
):
    captured: dict[str, str] = {}

    def fake_prompt(message: str, default: str = "") -> str:
        captured["message"] = message
        captured["default"] = default
        return "  bugfix/1-edited  "

    monkeypatch.setattr("prompt_toolkit.prompt", fake_prompt)

    result = edit_branch_name("bugfix/1-fix-login")

    assert captured == {"message": "Branch name: ", "default": "bugfix/1-fix-login"}
    assert result == "bugfix/1-edited"
