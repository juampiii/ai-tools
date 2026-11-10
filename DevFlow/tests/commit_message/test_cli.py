import argparse
from typing import Any

import pytest

from devflow.commit_message import cli
from devflow.commit_message.cli import (
    edit_message,
    parse_args,
    parse_length_range,
    prompt_review,
    run,
)

# --- parse_args -----------------------------------------------------------------------------


def test_parse_args_uses_the_default_length_range():
    assert parse_args([]).length == (50, 70)


@pytest.mark.parametrize("flag", ["-l", "--length"])
def test_parse_args_accepts_the_short_and_long_length_flags(flag: str):
    assert parse_args([flag, "80-100"]).length == (80, 100)


@pytest.mark.parametrize("value", ["abc", "80", "80-", "-100", "100-80", "0-10", "80-100-120"])
def test_parse_length_range_rejects_invalid_values(value: str):
    with pytest.raises(argparse.ArgumentTypeError):
        parse_length_range(value)


def test_parse_args_rejects_an_invalid_range(capsys):
    with pytest.raises(SystemExit):
        parse_args(["--length", "nope"])

    assert "nope" in capsys.readouterr().err


# --- run ------------------------------------------------------------------------------------


def test_run_resolves_the_interrupt_and_prints_message_and_usage(graph, clipboard, capsys):
    shown: list[dict[str, Any]] = []

    def review(payload: dict[str, Any]) -> dict[str, Any]:
        shown.append(payload)
        return {"action": "approve"}

    exit_code = run(graph, 50, 70, review)

    output = capsys.readouterr().out
    assert exit_code == 0
    assert shown[0]["message"].startswith("fix: Prevent costs validation")
    assert f"Copied to the clipboard: {shown[0]['message']}" in output
    assert "10 input tokens" in output
    assert "5 output tokens" in output
    assert clipboard.copied == [shown[0]["message"]]


def test_run_sends_the_length_range_to_the_llm(graph, llm):
    run(graph, 80, 100, lambda payload: {"action": "approve"})

    assert "80 to 100 characters" in llm.calls[0][0]


def test_run_prints_the_error_and_returns_failure_code(graph, git, capsys):
    git.branch_error = "fatal: not a git repository"

    exit_code = run(graph, 50, 70, lambda payload: {"action": "approve"})

    assert exit_code == 1
    assert "not a git repository" in capsys.readouterr().err


# --- prompt_review --------------------------------------------------------------------------

REVIEW_PAYLOAD = {
    "branch_name": "feature/52691-x",
    "changed_files": ["M src/app.py", "?? src/new.py"],
    "message": "fix: Do it. story: #52691",
}


def answer_with(monkeypatch: pytest.MonkeyPatch, *answers: str) -> list[str]:
    asked: list[str] = []
    remaining = list(answers)

    def fake_input(prompt: str = "") -> str:
        asked.append(prompt)
        return remaining.pop(0)

    monkeypatch.setattr("builtins.input", fake_input)
    return asked


def test_prompt_review_shows_branch_files_and_message(monkeypatch: pytest.MonkeyPatch, capsys):
    answer_with(monkeypatch, "a")

    prompt_review(REVIEW_PAYLOAD)

    output = capsys.readouterr().out
    assert "feature/52691-x" in output
    assert "M src/app.py" in output
    assert "?? src/new.py" in output
    assert "fix: Do it. story: #52691" in output


def test_prompt_review_lists_only_the_first_files_when_there_are_many(
    monkeypatch: pytest.MonkeyPatch, capsys
):
    answer_with(monkeypatch, "a")
    files = [f"M src/file{i}.py" for i in range(20)]

    prompt_review({**REVIEW_PAYLOAD, "changed_files": files})

    output = capsys.readouterr().out
    assert "src/file14.py" in output
    assert "src/file15.py" not in output
    assert "and 5 more" in output


@pytest.mark.parametrize("answer", ["a", "A", "approve"])
def test_prompt_review_approves(monkeypatch: pytest.MonkeyPatch, answer: str):
    answer_with(monkeypatch, answer)

    assert prompt_review(REVIEW_PAYLOAD) == {"action": "approve"}


def test_prompt_review_edit_starts_from_the_proposed_message(monkeypatch: pytest.MonkeyPatch):
    answer_with(monkeypatch, "e")
    received: list[str] = []

    def fake_edit(current: str) -> str:
        received.append(current)
        return "fix: Edited."

    monkeypatch.setattr(cli, "edit_message", fake_edit)

    result = prompt_review(REVIEW_PAYLOAD)

    assert received == ["fix: Do it. story: #52691"]
    assert result == {"action": "edit", "message": "fix: Edited."}


def test_prompt_review_reject_returns_the_feedback(monkeypatch: pytest.MonkeyPatch):
    answer_with(monkeypatch, "r", "too vague")

    assert prompt_review(REVIEW_PAYLOAD) == {"action": "reject", "feedback": "too vague"}


def test_prompt_review_asks_again_after_an_invalid_option(monkeypatch: pytest.MonkeyPatch, capsys):
    asked = answer_with(monkeypatch, "x", "a")

    result = prompt_review(REVIEW_PAYLOAD)

    assert result == {"action": "approve"}
    assert len(asked) == 2
    assert "Invalid option" in capsys.readouterr().out


# --- edit_message ---------------------------------------------------------------------------


def test_edit_message_prefills_the_current_message_and_trims_the_result(
    monkeypatch: pytest.MonkeyPatch,
):
    captured: dict[str, str] = {}

    def fake_prompt(message: str, default: str = "") -> str:
        captured["message"] = message
        captured["default"] = default
        return "  fix: Edited.  "

    monkeypatch.setattr("prompt_toolkit.prompt", fake_prompt)

    result = edit_message("fix: Do it.")

    assert captured == {"message": "Commit message: ", "default": "fix: Do it."}
    assert result == "fix: Edited."
