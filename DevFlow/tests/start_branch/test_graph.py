from typing import Any

from langgraph.graph.state import CompiledStateGraph
from langgraph.types import Command

from devflow.shared.tracker import Card
from tests.fakes import FakeGitClient, FakeLlmClient, FakeTrackerClient, slug_json

CARD_ID = 12345


def start(graph: CompiledStateGraph, config: dict) -> dict[str, Any]:
    return graph.invoke({"card_id": CARD_ID}, config)


def resume(graph: CompiledStateGraph, config: dict, decision: dict[str, Any]) -> dict[str, Any]:
    return graph.invoke(Command(resume=decision), config)


def interrupt_payload(result: dict[str, Any]) -> dict[str, Any]:
    return result["__interrupt__"][0].value


def created_branches(git: FakeGitClient) -> list[tuple[str, str, str]]:
    return [call for call in git.calls if call[0] == "create_branch"]


def test_approved_bug_creates_a_bugfix_branch_from_origin_develop(graph, git, thread_config):
    result = start(graph, thread_config)
    assert interrupt_payload(result)["branch_name"] == "bugfix/12345-fix-login-error"

    result = resume(graph, thread_config, {"action": "approve"})

    assert result["created_branch"] == "bugfix/12345-fix-login-error"
    assert git.calls == [
        ("fetch", "origin", "develop"),
        ("create_branch", "bugfix/12345-fix-login-error", "origin/develop"),
    ]


def test_approved_user_story_creates_a_feature_branch(graph, tracker, git, thread_config):
    tracker.card = Card(id=CARD_ID, title="Add export", type="User Story")

    start(graph, thread_config)
    result = resume(graph, thread_config, {"action": "approve"})

    assert result["created_branch"].startswith("feature/12345-")
    assert created_branches(git) == [("create_branch", result["created_branch"], "origin/develop")]


def test_unsupported_card_type_ends_with_error_and_does_not_call_git(
    graph, tracker, git, thread_config
):
    tracker.card = Card(id=CARD_ID, title="Some task", type="Task")

    result = start(graph, thread_config)

    assert "Task" in result["error"]
    assert "__interrupt__" not in result
    assert git.calls == []


def test_card_not_found_ends_with_error_and_does_not_call_git(graph, tracker, git, thread_config):
    tracker.error = "Card 12345 does not exist in Azure DevOps."

    result = start(graph, thread_config)

    assert result["error"] == "Card 12345 does not exist in Azure DevOps."
    assert git.calls == []


def test_fetch_failure_ends_with_error_and_does_not_call_llm(graph, git, llm, thread_config):
    git.fetch_error = "fatal: unable to access remote"

    result = start(graph, thread_config)

    assert "unable to access remote" in result["error"]
    assert llm.calls == []
    assert created_branches(git) == []


def test_llm_failure_ends_with_error_and_does_not_create_the_branch(graph, git, llm, thread_config):
    llm.error = "The LLM CLI failed (502): boom"

    result = start(graph, thread_config)

    assert "502" in result["error"]
    assert "__interrupt__" not in result
    assert created_branches(git) == []


def test_rejection_with_feedback_then_approval_calls_llm_twice_with_feedback(
    tracker: FakeTrackerClient, git: FakeGitClient, thread_config
):
    from langgraph.checkpoint.memory import InMemorySaver

    from devflow.start_branch.graph import build_graph

    llm = FakeLlmClient(responses=[slug_json("fix-login-error"), slug_json("login-fix")])
    graph = build_graph(tracker, llm, git, InMemorySaver(), "develop")

    start(graph, thread_config)
    result = resume(graph, thread_config, {"action": "reject", "feedback": "make it shorter"})
    assert interrupt_payload(result)["branch_name"] == "bugfix/12345-login-fix"
    result = resume(graph, thread_config, {"action": "approve"})

    assert len(llm.calls) == 2
    assert "make it shorter" not in llm.calls[0][0]
    assert "make it shorter" in llm.calls[1][0]
    assert result["created_branch"] == "bugfix/12345-login-fix"
    assert result["llm_input_tokens"] == 20
    assert result["llm_output_tokens"] == 10


def test_rejection_without_feedback_tells_the_llm_not_to_repeat_the_rejected_slug(
    tracker: FakeTrackerClient, git: FakeGitClient, thread_config
):
    from langgraph.checkpoint.memory import InMemorySaver

    from devflow.start_branch.graph import build_graph

    llm = FakeLlmClient(responses=[slug_json("fix-login-error"), slug_json("login-fix")])
    graph = build_graph(tracker, llm, git, InMemorySaver(), "develop")

    start(graph, thread_config)
    resume(graph, thread_config, {"action": "reject", "feedback": ""})

    assert "fix-login-error" not in llm.calls[0][0]
    assert "- fix-login-error" in llm.calls[1][0]


def test_every_rejected_slug_is_excluded_from_later_proposals(
    tracker: FakeTrackerClient, git: FakeGitClient, thread_config
):
    from langgraph.checkpoint.memory import InMemorySaver

    from devflow.start_branch.graph import build_graph

    llm = FakeLlmClient(responses=[slug_json("first"), slug_json("second"), slug_json("third")])
    graph = build_graph(tracker, llm, git, InMemorySaver(), "develop")

    start(graph, thread_config)
    resume(graph, thread_config, {"action": "reject"})
    result = resume(graph, thread_config, {"action": "reject"})

    third_prompt = llm.calls[2][0]
    assert "- first" in third_prompt
    assert "- second" in third_prompt
    assert interrupt_payload(result)["branch_name"] == "bugfix/12345-third"


def test_manual_edit_creates_the_branch_with_the_edited_name(graph, git, thread_config):
    start(graph, thread_config)

    result = resume(
        graph, thread_config, {"action": "edit", "branch_name": "bugfix/12345-my-own-name"}
    )

    assert result["created_branch"] == "bugfix/12345-my-own-name"
    assert created_branches(git) == [
        ("create_branch", "bugfix/12345-my-own-name", "origin/develop")
    ]


def test_edit_with_empty_name_ends_with_error_and_does_not_create_the_branch(
    graph, git, thread_config
):
    start(graph, thread_config)

    result = resume(graph, thread_config, {"action": "edit", "branch_name": "   "})

    assert "empty" in result["error"]
    assert created_branches(git) == []


def test_unknown_review_action_ends_with_error_and_does_not_create_the_branch(
    graph, git, thread_config
):
    start(graph, thread_config)

    result = resume(graph, thread_config, {"action": "maybe"})

    assert "maybe" in result["error"]
    assert created_branches(git) == []


def test_no_branch_is_created_before_the_human_approves(graph, git, thread_config):
    result = start(graph, thread_config)

    assert "__interrupt__" in result
    assert created_branches(git) == []


def test_no_branch_is_created_while_the_user_keeps_rejecting(graph, git, thread_config):
    start(graph, thread_config)
    resume(graph, thread_config, {"action": "reject", "feedback": "no"})
    result = resume(graph, thread_config, {"action": "reject", "feedback": "still no"})

    assert "__interrupt__" in result
    assert created_branches(git) == []


def test_branch_creation_failure_ends_with_error(graph, git, thread_config):
    git.create_error = "fatal: a branch named 'x' already exists"
    start(graph, thread_config)

    result = resume(graph, thread_config, {"action": "approve"})

    assert "already exists" in result["error"]
    assert "created_branch" not in result
