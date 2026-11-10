import json
from collections.abc import Callable

import httpx
import pytest

from devflow.shared.errors import ClientError
from devflow.shared.llm_client import HttpLlmClient, LlmResponse

API_URL = "http://llm.test/api/prompts"
API_KEY = "test-key"
SCHEMA = {"type": "object", "properties": {"slug": {"type": "string"}}}
OK_BODY = {
    "response": '{"slug": "fix-login"}',
    "model": "claude-test",
    "inputTokens": 120,
    "outputTokens": 8,
    "cost": 0.0042,
}


def make_client(handler: Callable[[httpx.Request], httpx.Response]) -> HttpLlmClient:
    http = httpx.Client(transport=httpx.MockTransport(handler))
    return HttpLlmClient(API_URL, API_KEY, http_client=http)


def test_complete_parses_the_response():
    client = make_client(lambda request: httpx.Response(200, json=OK_BODY))

    result = client.complete("prompt", "Low", SCHEMA)

    assert result == LlmResponse(
        response='{"slug": "fix-login"}',
        model="claude-test",
        input_tokens=120,
        output_tokens=8,
        cost=0.0042,
    )


def test_complete_sends_the_expected_body_to_the_configured_url():
    captured: list[httpx.Request] = []

    def handler(request: httpx.Request) -> httpx.Response:
        captured.append(request)
        return httpx.Response(200, json=OK_BODY)

    make_client(handler).complete("my prompt", "Low", SCHEMA)

    request = captured[0]
    assert request.method == "POST"
    assert str(request.url) == API_URL
    assert request.headers["X-Api-Key"] == API_KEY
    assert json.loads(request.content) == {
        "prompt": "my prompt",
        "complexity": "Low",
        "jsonSchema": SCHEMA,
    }


def test_complete_sends_nulls_when_complexity_and_schema_are_omitted():
    captured: list[httpx.Request] = []

    def handler(request: httpx.Request) -> httpx.Response:
        captured.append(request)
        return httpx.Response(200, json=OK_BODY)

    make_client(handler).complete("p", None, None)

    body = json.loads(captured[0].content)
    assert body["complexity"] is None
    assert body["jsonSchema"] is None


def test_complete_raises_clear_error_on_400():
    client = make_client(lambda request: httpx.Response(400, text="bad prompt"))

    with pytest.raises(ClientError, match="400.*bad prompt"):
        client.complete("p", "Low", None)


def test_complete_raises_clear_error_on_401():
    client = make_client(lambda request: httpx.Response(401))

    with pytest.raises(ClientError, match="401.*LLM_API_KEY"):
        client.complete("p", "Low", None)


def test_complete_raises_clear_error_on_502():
    client = make_client(lambda request: httpx.Response(502, text="cli failed"))

    with pytest.raises(ClientError, match="502.*cli failed"):
        client.complete("p", "Low", None)


def test_complete_raises_for_unexpected_status():
    client = make_client(lambda request: httpx.Response(500))

    with pytest.raises(ClientError, match="500"):
        client.complete("p", "Low", None)


def test_complete_raises_when_response_has_unexpected_shape():
    client = make_client(lambda request: httpx.Response(200, json={"response": "x"}))

    with pytest.raises(ClientError, match="expected format"):
        client.complete("p", "Low", None)


def test_complete_converts_timeout_to_client_error():
    def handler(request: httpx.Request) -> httpx.Response:
        raise httpx.ReadTimeout("timeout", request=request)

    with pytest.raises(ClientError, match="in time"):
        make_client(handler).complete("p", "Low", None)


def test_complete_converts_connection_failure_to_client_error():
    def handler(request: httpx.Request) -> httpx.Response:
        raise httpx.ConnectError("boom", request=request)

    with pytest.raises(ClientError, match="connect"):
        make_client(handler).complete("p", "Low", None)
