import base64
from collections.abc import Callable

import httpx
import pytest

from devflow.shared.ado_client import HttpAdoClient
from devflow.shared.errors import ClientError
from devflow.shared.tracker import Card


def make_client(handler: Callable[[httpx.Request], httpx.Response]) -> HttpAdoClient:
    http = httpx.Client(transport=httpx.MockTransport(handler))
    return HttpAdoClient("my-org", "My Project", "secret-pat", http_client=http)


def card_response(request: httpx.Request) -> httpx.Response:
    return httpx.Response(
        200,
        json={"fields": {"System.Title": "Fix login error", "System.WorkItemType": "Bug"}},
    )


def test_get_card_returns_title_and_type():
    client = make_client(card_response)

    card = client.get_card(12345)

    assert card == Card(id=12345, title="Fix login error", type="Bug")


def test_get_card_builds_the_expected_request():
    captured: list[httpx.Request] = []

    def handler(request: httpx.Request) -> httpx.Response:
        captured.append(request)
        return card_response(request)

    make_client(handler).get_card(12345)

    request = captured[0]
    assert request.method == "GET"
    assert request.url.path == "/my-org/My Project/_apis/wit/workitems/12345"
    assert request.url.raw_path.startswith(b"/my-org/My%20Project/_apis/wit/workitems/12345?")
    assert request.url.params["fields"] == "System.Title,System.WorkItemType"
    assert "api-version" in request.url.params


def test_get_card_authenticates_with_basic_auth_and_pat():
    captured: list[httpx.Request] = []

    def handler(request: httpx.Request) -> httpx.Response:
        captured.append(request)
        return card_response(request)

    make_client(handler).get_card(1)

    expected = base64.b64encode(b":secret-pat").decode()
    assert captured[0].headers["Authorization"] == f"Basic {expected}"


def test_get_card_raises_clear_error_when_card_does_not_exist():
    client = make_client(lambda request: httpx.Response(404))

    with pytest.raises(ClientError, match="12345"):
        client.get_card(12345)


@pytest.mark.parametrize("status", [203, 401, 403])
def test_get_card_raises_credentials_error_for_auth_failures(status: int):
    client = make_client(lambda request: httpx.Response(status))

    with pytest.raises(ClientError, match="ADO_PAT"):
        client.get_card(1)


def test_get_card_raises_for_unexpected_status():
    client = make_client(lambda request: httpx.Response(500))

    with pytest.raises(ClientError, match="500"):
        client.get_card(1)


def test_get_card_raises_when_response_has_unexpected_shape():
    client = make_client(lambda request: httpx.Response(200, json={"fields": {}}))

    with pytest.raises(ClientError, match="expected format"):
        client.get_card(1)


def test_get_card_raises_when_response_is_not_json():
    client = make_client(lambda request: httpx.Response(200, text="<html></html>"))

    with pytest.raises(ClientError, match="expected format"):
        client.get_card(1)


def test_get_card_converts_timeout_to_client_error():
    def handler(request: httpx.Request) -> httpx.Response:
        raise httpx.ReadTimeout("timeout", request=request)

    with pytest.raises(ClientError, match="in time"):
        make_client(handler).get_card(1)


def test_get_card_converts_connection_failure_to_client_error():
    def handler(request: httpx.Request) -> httpx.Response:
        raise httpx.ConnectError("boom", request=request)

    with pytest.raises(ClientError, match="connect"):
        make_client(handler).get_card(1)
