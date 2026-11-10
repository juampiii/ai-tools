from langgraph.graph import END

from devflow.start_branch.state import StartBranchState


def _next_or_end(state: StartBranchState, next_node: str) -> str:
    return END if state.get("error") else next_node


def route_after_read_card(state: StartBranchState) -> str:
    return _next_or_end(state, "resolve_prefix")


def route_after_resolve_prefix(state: StartBranchState) -> str:
    return _next_or_end(state, "git_fetch")


def route_after_git_fetch(state: StartBranchState) -> str:
    return _next_or_end(state, "propose_name")


def route_after_propose_name(state: StartBranchState) -> str:
    return _next_or_end(state, "human_review")


def route_after_human_review(state: StartBranchState) -> str:
    if state.get("error"):
        return END
    if state.get("review_action") == "reject":
        return "propose_name"
    return "create_branch"
