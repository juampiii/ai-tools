from langgraph.graph import END

from devflow.commit_message.state import CommitMessageState


def _next_or_end(state: CommitMessageState, next_node: str) -> str:
    return END if state.get("error") else next_node


def route_after_read_branch(state: CommitMessageState) -> str:
    return _next_or_end(state, "read_changes")


def route_after_read_changes(state: CommitMessageState) -> str:
    return _next_or_end(state, "propose_message")


def route_after_propose_message(state: CommitMessageState) -> str:
    return _next_or_end(state, "human_review")


def route_after_human_review(state: CommitMessageState) -> str:
    if state.get("error"):
        return END
    if state.get("review_action") == "reject":
        return "propose_message"
    return "copy_message"
