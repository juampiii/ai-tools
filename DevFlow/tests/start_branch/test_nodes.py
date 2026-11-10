import pytest

from devflow.shared.tracker import Card
from devflow.start_branch.nodes import (
    MAX_SLUG_LENGTH,
    SLUG_JSON_SCHEMA,
    make_create_branch,
    make_git_fetch,
    make_propose_name,
    make_read_card,
    normalize_slug,
    resolve_prefix,
)
from tests.fakes import FakeGitClient, FakeLlmClient, FakeTrackerClient, slug_json

# --- normalize_slug -------------------------------------------------------------------------


@pytest.mark.parametrize(
    ("raw", "expected"),
    [
        ("Fix Login Error", "fix-login-error"),
        ("  fix_login--error!  ", "fix-login-error"),
        ("already-kebab-case", "already-kebab-case"),
        ("", ""),
        ("!!!", ""),
    ],
)
def test_normalize_slug_produces_lowercase_kebab_case(raw, expected):
    assert normalize_slug(raw) == expected


def test_normalize_slug_truncates_on_a_word_boundary():
    raw = "-".join(["word"] * 30)

    slug = normalize_slug(raw)

    assert len(slug) <= MAX_SLUG_LENGTH
    assert slug == "-".join(["word"] * 10)


def test_normalize_slug_cuts_a_single_long_word_at_the_limit():
    assert normalize_slug("a" * 80) == "a" * MAX_SLUG_LENGTH


# --- read_card ------------------------------------------------------------------------------


def test_read_card_returns_title_and_type():
    tracker = FakeTrackerClient(card=Card(id=7, title="Some title", type="Bug"))

    result = make_read_card(tracker)({"card_id": 7})

    assert result == {"card_title": "Some title", "card_type": "Bug"}
    assert tracker.calls == [7]


def test_read_card_returns_error_when_client_fails():
    tracker = FakeTrackerClient(error="Card 7 does not exist in Azure DevOps.")

    result = make_read_card(tracker)({"card_id": 7})

    assert result == {"error": "Card 7 does not exist in Azure DevOps."}


# --- resolve_prefix -------------------------------------------------------------------------


def test_resolve_prefix_returns_bugfix_for_bug():
    assert resolve_prefix({"card_type": "Bug"}) == {"branch_prefix": "bugfix/"}


def test_resolve_prefix_returns_feature_for_user_story():
    assert resolve_prefix({"card_type": "User Story"}) == {"branch_prefix": "feature/"}


def test_resolve_prefix_returns_feature_for_product_backlog_item():
    assert resolve_prefix({"card_type": "Product Backlog Item"}) == {"branch_prefix": "feature/"}


def test_resolve_prefix_returns_feature_for_github_issue():
    assert resolve_prefix({"card_type": "Issue"}) == {"branch_prefix": "feature/"}


def test_resolve_prefix_returns_error_for_unsupported_type():
    result = resolve_prefix({"card_type": "Task"})

    assert "Task" in result["error"]
    assert "branch_prefix" not in result


# --- git_fetch ------------------------------------------------------------------------------


def test_git_fetch_fetches_the_base_branch_from_origin():
    git = FakeGitClient()

    result = make_git_fetch(git, "develop")({})

    assert result == {}
    assert git.calls == [("fetch", "origin", "develop")]


def test_git_fetch_returns_error_when_git_fails():
    git = FakeGitClient(fetch_error="fatal: no remote")

    result = make_git_fetch(git, "develop")({})

    assert result == {"error": "fatal: no remote"}


# --- propose_name ---------------------------------------------------------------------------


def propose_state(**overrides):
    state = {"card_id": 12345, "card_title": "Fix login error", "branch_prefix": "bugfix/"}
    return {**state, **overrides}


def test_propose_name_builds_name_from_prefix_id_and_slug():
    llm = FakeLlmClient(responses=[slug_json("fix-login-error")])

    result = make_propose_name(llm)(propose_state())

    assert result["branch_name"] == "bugfix/12345-fix-login-error"


def test_propose_name_sets_prefix_and_id_in_code_even_if_the_llm_adds_them():
    llm = FakeLlmClient(responses=[slug_json("feature/99-Fix Login")])

    result = make_propose_name(llm)(propose_state())

    assert result["branch_name"] == "bugfix/12345-feature-99-fix-login"


def test_propose_name_normalizes_the_llm_output():
    llm = FakeLlmClient(responses=[slug_json("  Fix_Login ERROR!! ")])

    result = make_propose_name(llm)(propose_state())

    assert result["branch_name"] == "bugfix/12345-fix-login-error"


def test_propose_name_asks_the_llm_for_a_structured_low_complexity_answer():
    llm = FakeLlmClient()

    make_propose_name(llm)(propose_state())

    _, complexity, schema = llm.calls[0]
    assert complexity == "Low"
    assert schema == SLUG_JSON_SCHEMA


def test_propose_name_prompt_includes_the_card_title():
    llm = FakeLlmClient()

    make_propose_name(llm)(propose_state(card_title="Error al iniciar sesión"))

    assert "Error al iniciar sesión" in llm.calls[0][0]


def test_propose_name_prompt_omits_feedback_when_there_is_none():
    llm = FakeLlmClient()

    make_propose_name(llm)(propose_state(feedback=None))

    assert "rejected" not in llm.calls[0][0]


def test_propose_name_prompt_includes_feedback_from_a_previous_rejection():
    llm = FakeLlmClient()

    make_propose_name(llm)(propose_state(feedback="make it shorter"))

    assert "make it shorter" in llm.calls[0][0]


def test_propose_name_returns_the_normalized_slug():
    llm = FakeLlmClient(responses=[slug_json("Fix Login")])

    result = make_propose_name(llm)(propose_state())

    assert result["branch_slug"] == "fix-login"


def test_propose_name_prompt_omits_rejected_slugs_when_there_are_none():
    llm = FakeLlmClient()

    make_propose_name(llm)(propose_state())

    assert "already rejected" not in llm.calls[0][0]


def test_propose_name_prompt_lists_every_rejected_slug():
    llm = FakeLlmClient()

    make_propose_name(llm)(propose_state(rejected_slugs=["first-slug", "second-slug"]))

    prompt = llm.calls[0][0]
    assert "already rejected" in prompt
    assert "- first-slug" in prompt
    assert "- second-slug" in prompt


def test_propose_name_accumulates_llm_usage():
    llm = FakeLlmClient(input_tokens=10, output_tokens=5, cost=0.01)
    state = propose_state(llm_input_tokens=100, llm_output_tokens=50, llm_cost=0.5)

    result = make_propose_name(llm)(state)

    assert result["llm_input_tokens"] == 110
    assert result["llm_output_tokens"] == 55
    assert result["llm_cost"] == pytest.approx(0.51)


def test_propose_name_returns_error_when_llm_fails():
    llm = FakeLlmClient(error="The LLM CLI failed (502)")

    result = make_propose_name(llm)(propose_state())

    assert result == {"error": "The LLM CLI failed (502)"}


@pytest.mark.parametrize("response", ["not json", '{"other": "x"}', '{"slug": 5}', "[]"])
def test_propose_name_returns_error_when_llm_output_is_invalid(response):
    llm = FakeLlmClient(responses=[response])

    result = make_propose_name(llm)(propose_state())

    assert "error" in result
    assert "branch_name" not in result


def test_propose_name_returns_error_when_slug_is_empty_after_normalizing():
    llm = FakeLlmClient(responses=[slug_json("!!!")])

    result = make_propose_name(llm)(propose_state())

    assert "empty" in result["error"]


# --- create_branch --------------------------------------------------------------------------


def test_create_branch_creates_it_from_origin_base_branch():
    git = FakeGitClient()

    result = make_create_branch(git, "develop")({"branch_name": "bugfix/1-x"})

    assert result == {"created_branch": "bugfix/1-x"}
    assert git.calls == [("create_branch", "bugfix/1-x", "origin/develop")]


def test_create_branch_returns_error_when_git_fails():
    git = FakeGitClient(create_error="fatal: already exists")

    result = make_create_branch(git, "develop")({"branch_name": "bugfix/1-x"})

    assert result == {"error": "fatal: already exists"}
