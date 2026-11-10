from langgraph.graph import END

from devflow.commit_message.routing import (
    route_after_human_review,
    route_after_propose_message,
    route_after_read_branch,
    route_after_read_changes,
)


def test_route_after_read_branch_goes_to_read_changes():
    assert route_after_read_branch({}) == "read_changes"


def test_route_after_read_branch_ends_on_error():
    assert route_after_read_branch({"error": "boom"}) == END


def test_route_after_read_changes_goes_to_propose_message():
    assert route_after_read_changes({}) == "propose_message"


def test_route_after_read_changes_ends_on_error():
    assert route_after_read_changes({"error": "boom"}) == END


def test_route_after_propose_message_goes_to_human_review():
    assert route_after_propose_message({}) == "human_review"


def test_route_after_propose_message_ends_on_error():
    assert route_after_propose_message({"error": "boom"}) == END


def test_route_after_human_review_copies_the_message_when_approved():
    assert route_after_human_review({"review_action": "approve"}) == "copy_message"


def test_route_after_human_review_copies_the_message_when_edited():
    assert route_after_human_review({"review_action": "edit"}) == "copy_message"


def test_route_after_human_review_proposes_again_when_rejected():
    assert route_after_human_review({"review_action": "reject"}) == "propose_message"


def test_route_after_human_review_ends_on_error():
    assert route_after_human_review({"review_action": "approve", "error": "boom"}) == END
