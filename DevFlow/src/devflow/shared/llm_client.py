from dataclasses import dataclass
from typing import Any, Literal, Protocol

import httpx

from devflow.shared.errors import ClientError

Complexity = Literal["Low", "Medium", "High", "VeryHigh", "Max"]

# Every call starts the Claude Code CLI, so the timeout is generous.
DEFAULT_TIMEOUT_SECONDS = 120.0
API_KEY_HEADER = "X-Api-Key"
MAX_ERROR_DETAIL_LENGTH = 300


@dataclass(frozen=True)
class LlmResponse:
    response: str
    model: str
    input_tokens: int
    output_tokens: int
    cost: float


class LlmClient(Protocol):
    def complete(
        self,
        prompt: str,
        complexity: Complexity | None,
        json_schema: dict[str, Any] | None,
    ) -> LlmResponse: ...


class HttpLlmClient:
    """Client for the local LLM API (`POST /api/prompts`)."""

    def __init__(
        self,
        api_url: str,
        api_key: str,
        http_client: httpx.Client | None = None,
        timeout: float = DEFAULT_TIMEOUT_SECONDS,
    ) -> None:
        self._api_url = api_url
        self._api_key = api_key
        self._http = http_client or httpx.Client()
        self._timeout = timeout

    def complete(
        self,
        prompt: str,
        complexity: Complexity | None,
        json_schema: dict[str, Any] | None,
    ) -> LlmResponse:
        body = {"prompt": prompt, "complexity": complexity, "jsonSchema": json_schema}

        try:
            response = self._http.post(
                self._api_url,
                json=body,
                headers={API_KEY_HEADER: self._api_key},
                timeout=self._timeout,
            )
        except httpx.TimeoutException as exc:
            raise ClientError("The LLM API did not respond in time.") from exc
        except httpx.HTTPError as exc:
            raise ClientError(f"Could not connect to the LLM API: {exc}") from exc

        if response.status_code == 400:
            raise ClientError(f"The LLM API rejected the request (400): {self._detail(response)}")
        if response.status_code == 401:
            raise ClientError("The LLM API rejected the API key (401). Check LLM_API_KEY.")
        if response.status_code == 502:
            raise ClientError(f"The LLM CLI failed (502): {self._detail(response)}")
        if response.status_code != 200:
            raise ClientError(f"The LLM API answered with status {response.status_code}.")

        return self._parse_response(response)

    @staticmethod
    def _detail(response: httpx.Response) -> str:
        return response.text.strip()[:MAX_ERROR_DETAIL_LENGTH] or "no detail"

    @staticmethod
    def _parse_response(response: httpx.Response) -> LlmResponse:
        try:
            data = response.json()
            return LlmResponse(
                response=data["response"],
                model=data["model"],
                input_tokens=int(data["inputTokens"]),
                output_tokens=int(data["outputTokens"]),
                cost=float(data["cost"]),
            )
        except (ValueError, KeyError, TypeError) as exc:
            raise ClientError("The LLM API response does not have the expected format.") from exc
