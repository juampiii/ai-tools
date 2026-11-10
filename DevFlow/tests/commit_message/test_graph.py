from typing import Any

from langgraph.graph.state import CompiledStateGraph
from langgraph.types import Command

from devflow.shared.git_client import FileChange
from tests.fakes import message_json

EXPECTED_MESSAGE = "fix: Prevent costs validation for an elearning product. story: #52691"


def start(graph: CompiledStateGraph, config: dict) -> dict[str, Any]:
    return graph.invoke({"min_length": 50, "max_length": 70}, config)


def resume(graph: CompiledStateGraph, config: dict, decision: dict[str, Any]) -> dict[str, Any]:
    return graph.invoke(Command(resume=decision), config)


def interrupt_payload(result: dict[str, Any]) -> dict[str, Any]:
    return result["__interrupt__"][0].value


def test_approved_message_is_copied_to_the_clipboard(graph, clipboard, thread_config):
    result = start(graph, thread_config)
    assert interrupt_payload(result) == {
        "branch_name": "feature/52691-elearning-costs",
        "changed_files": ["M src/app.py"],
        "message": EXPECTED_MESSAGE,
    }

    result = resume(graph, thread_config, {"action": "approve"})

    assert result["copied_message"] == EXPECTED_MESSAGE
    assert clipboard.copied == [EXPECTED_MESSAGE]


def test_nothing_is_copied_before_the_approval(graph, clipboard, thread_config):
    start(graph, thread_config)

    assert clipboard.copied == []


def test_edited_message_is_the_one_copied(graph, clipboard, thread_config):
    start(graph, thread_config)

    result = resume(graph, thread_config, {"action": "edit", "message": "fix: My own text."})

    assert result["copied_message"] == "fix: My own text."
    assert clipboard.copied == ["fix: My own text."]


def test_empty_edited_message_ends_with_error_and_copies_nothing(graph, clipboard, thread_config):
    start(graph, thread_config)

    result = resume(graph, thread_config, {"action": "edit", "message": "   "})

    assert "empty" in result["error"]
    assert clipboard.copied == []


def test_branch_without_story_code_gets_no_suffix(graph, git, llm, thread_config):
    git.branch = "main"
    llm.responses = [message_json("docs", "Update the local setup steps in the README")]

    result = start(graph, thread_config)

    assert (
        interrupt_payload(result)["message"] == "docs: Update the local setup steps in the README."
    )


def test_rejection_with_feedback_proposes_again_and_the_llm_receives_it(
    graph, llm, clipboard, thread_config
):
    llm.responses = [
        message_json("fix", "Change validation"),
        message_json("fix", "Prevent costs validation for an elearning product"),
    ]
    start(graph, thread_config)

    result = resume(graph, thread_config, {"action": "reject", "feedback": "mention elearning"})
    assert interrupt_payload(result)["message"] == EXPECTED_MESSAGE
    result = resume(graph, thread_config, {"action": "approve"})

    assert len(llm.calls) == 2
    assert "mention elearning" not in llm.calls[0][0]
    assert "mention elearning" in llm.calls[1][0]
    assert "- Change validation." in llm.calls[1][0]
    assert clipboard.copied == [EXPECTED_MESSAGE]
    assert result["llm_input_tokens"] == 20


def test_noise_files_are_not_sent_to_the_llm(graph, git, llm, thread_config):
    git.changes = [
        FileChange("src/app.py", "M"),
        FileChange(".claude/settings.json", "M"),
        FileChange("uv.lock", "M"),
    ]

    start(graph, thread_config)

    assert git.diff_calls == [["src/app.py"]]
    assert "settings.json" not in llm.calls[0][0]
    assert "uv.lock" not in llm.calls[0][0]


def test_no_meaningful_changes_ends_with_error_and_does_not_call_llm(
    graph, git, llm, thread_config
):
    git.changes = [FileChange(".gitignore", "M")]

    result = start(graph, thread_config)

    assert "no meaningful pending changes" in result["error"]
    assert "__interrupt__" not in result
    assert llm.calls == []


def test_git_failure_ends_with_error_and_does_not_call_llm(graph, git, llm, thread_config):
    git.branch_error = "fatal: not a git repository"

    result = start(graph, thread_config)

    assert "not a git repository" in result["error"]
    assert llm.calls == []


def test_llm_failure_ends_with_error_and_nothing_is_copied(graph, llm, clipboard, thread_config):
    llm.error = "The LLM CLI failed (502): boom"

    result = start(graph, thread_config)

    assert "502" in result["error"]
    assert "__interrupt__" not in result
    assert clipboard.copied == []


def test_clipboard_failure_ends_with_error_that_keeps_the_message(graph, clipboard, thread_config):
    clipboard.error = "`clip` failed: no detail"
    start(graph, thread_config)

    result = resume(graph, thread_config, {"action": "approve"})

    assert "`clip` failed" in result["error"]
    assert EXPECTED_MESSAGE in result["error"]
