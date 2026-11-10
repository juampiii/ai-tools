from urllib.parse import quote

import httpx

from devflow.shared.errors import ClientError
from devflow.shared.tracker import Card

API_VERSION = "7.1"
FIELD_TITLE = "System.Title"
FIELD_TYPE = "System.WorkItemType"
DEFAULT_TIMEOUT_SECONDS = 30.0


class HttpAdoClient:
    """Client for the Azure DevOps REST API (Basic auth with a PAT)."""

    def __init__(
        self,
        organization: str,
        project: str,
        pat: str,
        http_client: httpx.Client | None = None,
        timeout: float = DEFAULT_TIMEOUT_SECONDS,
    ) -> None:
        self._organization = organization
        self._project = project
        self._auth = httpx.BasicAuth("", pat)
        self._http = http_client or httpx.Client()
        self._timeout = timeout

    def get_card(self, card_id: int) -> Card:
        url = (
            f"https://dev.azure.com/{quote(self._organization, safe='')}"
            f"/{quote(self._project, safe='')}/_apis/wit/workitems/{card_id}"
        )
        params = {"fields": f"{FIELD_TITLE},{FIELD_TYPE}", "api-version": API_VERSION}

        try:
            response = self._http.get(url, params=params, auth=self._auth, timeout=self._timeout)
        except httpx.TimeoutException as exc:
            raise ClientError("Azure DevOps did not respond in time.") from exc
        except httpx.HTTPError as exc:
            raise ClientError(f"Could not connect to Azure DevOps: {exc}") from exc

        if response.status_code == 404:
            raise ClientError(f"Card {card_id} does not exist in Azure DevOps.")
        # With an invalid PAT, ADO sometimes answers 203 with the HTML login page.
        if response.status_code in (203, 401, 403):
            raise ClientError("Azure DevOps rejected the credentials. Check ADO_PAT.")
        if response.status_code != 200:
            raise ClientError(f"Azure DevOps answered with status {response.status_code}.")

        return self._parse_card(card_id, response)

    @staticmethod
    def _parse_card(card_id: int, response: httpx.Response) -> Card:
        try:
            fields = response.json()["fields"]
            return Card(id=card_id, title=fields[FIELD_TITLE], type=fields[FIELD_TYPE])
        except (ValueError, KeyError, TypeError) as exc:
            raise ClientError(
                "The Azure DevOps response does not have the expected format."
            ) from exc
