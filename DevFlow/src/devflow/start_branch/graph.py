from langgraph.checkpoint.base import BaseCheckpointSaver
from langgraph.graph import END, START, StateGraph
from langgraph.graph.state import CompiledStateGraph

from devflow.shared.git_client import GitClient
from devflow.shared.llm_client import LlmClient
from devflow.shared.tracker import TrackerClient
from devflow.start_branch.nodes import (
    human_review,
    make_create_branch,
    make_git_fetch,
    make_propose_name,
    make_read_card,
    resolve_prefix,
)
from devflow.start_branch.routing import (
    route_after_git_fetch,
    route_after_human_review,
    route_after_propose_name,
    route_after_read_card,
    route_after_resolve_prefix,
)
from devflow.start_branch.state import StartBranchState


def build_graph(
    tracker: TrackerClient,
    llm: LlmClient,
    git: GitClient,
    checkpointer: BaseCheckpointSaver,
    base_branch: str,
) -> CompiledStateGraph:
    builder = StateGraph(StartBranchState)

    builder.add_node("read_card", make_read_card(tracker))
    builder.add_node("resolve_prefix", resolve_prefix)
    builder.add_node("git_fetch", make_git_fetch(git, base_branch))
    builder.add_node("propose_name", make_propose_name(llm))
    builder.add_node("human_review", human_review)
    builder.add_node("create_branch", make_create_branch(git, base_branch))

    builder.add_edge(START, "read_card")
    builder.add_conditional_edges("read_card", route_after_read_card, ["resolve_prefix", END])
    builder.add_conditional_edges("resolve_prefix", route_after_resolve_prefix, ["git_fetch", END])
    builder.add_conditional_edges("git_fetch", route_after_git_fetch, ["propose_name", END])
    builder.add_conditional_edges("propose_name", route_after_propose_name, ["human_review", END])
    builder.add_conditional_edges(
        "human_review", route_after_human_review, ["propose_name", "create_branch", END]
    )
    builder.add_edge("create_branch", END)

    return builder.compile(checkpointer=checkpointer)
