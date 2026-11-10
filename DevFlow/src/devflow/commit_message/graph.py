from langgraph.checkpoint.base import BaseCheckpointSaver
from langgraph.graph import END, START, StateGraph
from langgraph.graph.state import CompiledStateGraph

from devflow.commit_message.nodes import (
    human_review,
    make_copy_message,
    make_propose_message,
    make_read_branch,
    make_read_changes,
)
from devflow.commit_message.routing import (
    route_after_human_review,
    route_after_propose_message,
    route_after_read_branch,
    route_after_read_changes,
)
from devflow.commit_message.state import CommitMessageState
from devflow.shared.clipboard_client import ClipboardClient
from devflow.shared.git_client import GitClient
from devflow.shared.llm_client import LlmClient


def build_graph(
    llm: LlmClient,
    git: GitClient,
    clipboard: ClipboardClient,
    checkpointer: BaseCheckpointSaver,
) -> CompiledStateGraph:
    builder = StateGraph(CommitMessageState)

    builder.add_node("read_branch", make_read_branch(git))
    builder.add_node("read_changes", make_read_changes(git))
    builder.add_node("propose_message", make_propose_message(llm))
    builder.add_node("human_review", human_review)
    builder.add_node("copy_message", make_copy_message(clipboard))

    builder.add_edge(START, "read_branch")
    builder.add_conditional_edges("read_branch", route_after_read_branch, ["read_changes", END])
    builder.add_conditional_edges(
        "read_changes", route_after_read_changes, ["propose_message", END]
    )
    builder.add_conditional_edges(
        "propose_message", route_after_propose_message, ["human_review", END]
    )
    builder.add_conditional_edges(
        "human_review", route_after_human_review, ["propose_message", "copy_message", END]
    )
    builder.add_edge("copy_message", END)

    return builder.compile(checkpointer=checkpointer)
