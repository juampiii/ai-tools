from collections.abc import Callable
from typing import Any

import httpx
import pytest

from devflow.shared.errors import ClientError
from devflow.shared.github_client import GitHubRepo, HttpGitHubClient, parse_github_remote
from devflow.shared.tracker import Card

REPO = GitHubRepo(owner="acme", name="my-repo")


def make_client(handler: Callable[[httpx.Request], httpx.Response]) -> HttpGitHubClient:
    http = httpx.Client(transport=httpx.MockTransport(handler))
    return HttpGitHubClient(REPO, "gh-secret", http_client=http)


def issue_json(labels: list[str] | None = None, **extra: Any) -> dict[str, Any]:
    return {
        "title": "Add CSV export",
        "labels": [{"name": name} for name in labels or []],
        **extra,
    }


# --- parse_github_remote --------------------------------------------------------------------


@pytest.mark.parametrize(
    "url",
    [
        "https://github.com/acme/my-repo.git",
        "https://github.com/acme/my-repo",
        "https://github.com/acme/my-repo/",
        "https://user:token@github.com/acme/my-repo.git",
        "http://github.com/acme/my-repo.git",
        "git@github.com:acme/my-repo.git",
        "git@github.com:acme/my-repo",
        "ssh://git@github.com/acme/my-repo.git",
        "  https://github.com/acme/my-repo.git\n",
    ],
)
def test_parse_github_remote_extracts_owner_and_repo(url: str):
    assert parse_github_remote(url) == REPO


def test_parse_github_remote_keeps_dots_inside_the_repo_name():
    assert parse_github_remote("git@github.com:acme/my.repo.git") == GitHubRepo("acme", "my.repo")


@pytest.mark.parametrize(
    "url",
    [
        "https://dev.azure.com/org/project/_git/repo",
        "git@ssh.dev.azure.com:v3/org/project/repo",
        "https://notgithub.com/acme/my-repo.git",
        "https://github.com/acme",
        "C:\\repos\\my-repo",
        "",
    ],
)
def test_parse_github_remote_rejects_remotes_that_are_not_github(url: str):
    with pytest.raises(ClientError, match="not a github.com repository"):
        parse_github_remote(url)


# --- get_card -------------------------------------------------------------------------------


def test_get_card_returns_an_issue_type_card_for_an_issue_without_bug_label():
    client = make_client(lambda request: httpx.Response(200, json=issue_json(["enhancement"])))

    card = client.get_card(42)

    assert card == Card(id=42, title="Add CSV export", type="Issue")


@pytest.mark.parametrize("label", ["bug", "Bug", "BUG"])
def test_get_card_returns_a_bug_type_card_when_the_issue_has_the_bug_label(label: str):
    client = make_client(lambda request: httpx.Response(200, json=issue_json(["x", label])))

    assert client.get_card(42).type == "Bug"


def test_get_card_builds_the_expected_request():
    captured: list[httpx.Request] = []

    def handler(request: httpx.Request) -> httpx.Response:
        captured.append(request)
        return httpx.Response(200, json=issue_json())

    make_client(handler).get_card(42)

    request = captured[0]
    assert request.method == "GET"
    assert str(request.url) == "https://api.github.com/repos/acme/my-repo/issues/42"
    assert request.headers["Authorization"] == "Bearer gh-secret"
    assert request.headers["Accept"] == "application/vnd.github+json"
    assert "X-GitHub-Api-Version" in request.headers


def test_get_card_raises_clear_error_when_the_issue_does_not_exist():
    client = make_client(lambda request: httpx.Response(404))

    with pytest.raises(ClientError, match="Issue 42 does not exist in acme/my-repo"):
        client.get_card(42)


@pytest.mark.parametrize("status", [401, 403])
def test_get_card_raises_credentials_error_for_auth_failures(status: int):
    client = make_client(lambda request: httpx.Response(status))

    with pytest.raises(ClientError, match="GITHUB_TOKEN"):
        client.get_card(42)


def test_get_card_raises_for_unexpected_status():
    client = make_client(lambda request: httpx.Response(500))

    with pytest.raises(ClientError, match="500"):
        client.get_card(42)


def test_get_card_raises_when_the_number_is_a_pull_request():
    body = issue_json(pull_request={"url": "https://api.github.com/..."})
    client = make_client(lambda request: httpx.Response(200, json=body))

    with pytest.raises(ClientError, match="pull request"):
        client.get_card(42)


def test_get_card_raises_when_response_has_unexpected_shape():
    client = make_client(lambda request: httpx.Response(200, json={"labels": []}))

    with pytest.raises(ClientError, match="expected format"):
        client.get_card(42)


def test_get_card_raises_when_response_is_not_json():
    client = make_client(lambda request: httpx.Response(200, text="<html></html>"))

    with pytest.raises(ClientError, match="expected format"):
        client.get_card(42)


def test_get_card_converts_timeout_to_client_error():
    def handler(request: httpx.Request) -> httpx.Response:
        raise httpx.ReadTimeout("timeout", request=request)

    with pytest.raises(ClientError, match="in time"):
        make_client(handler).get_card(42)


def test_get_card_converts_connection_failure_to_client_error():
    def handler(request: httpx.Request) -> httpx.Response:
        raise httpx.ConnectError("boom", request=request)

    with pytest.raises(ClientError, match="connect"):
        make_client(handler).get_card(42)
