import pytest
from langgraph.graph import END

from devflow.start_branch.routing import (
    route_after_git_fetch,
    route_after_human_review,
    route_after_propose_name,
    route_after_read_card,
    route_after_resolve_prefix,
)

SIMPLE_ROUTES = [
    (route_after_read_card, "resolve_prefix"),
    (route_after_resolve_prefix, "git_fetch"),
    (route_after_git_fetch, "propose_name"),
    (route_after_propose_name, "human_review"),
]


@pytest.mark.parametrize(("route", "expected"), SIMPLE_ROUTES)
def test_route_continues_to_next_node_when_there_is_no_error(route, expected):
    assert route({}) == expected


@pytest.mark.parametrize(("route", "expected"), SIMPLE_ROUTES)
def test_route_ends_when_there_is_an_error(route, expected):
    assert route({"error": "boom"}) == END


@pytest.mark.parametrize("action", ["approve", "edit"])
def test_route_after_human_review_creates_branch_on_approve_or_edit(action):
    assert route_after_human_review({"review_action": action}) == "create_branch"


def test_route_after_human_review_goes_back_to_propose_name_on_reject():
    assert route_after_human_review({"review_action": "reject"}) == "propose_name"


def test_route_after_human_review_ends_when_there_is_an_error():
    state = {"review_action": "reject", "error": "boom"}

    assert route_after_human_review(state) == END
