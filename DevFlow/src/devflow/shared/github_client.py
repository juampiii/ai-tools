import re
from dataclasses import dataclass

import httpx

from devflow.shared.errors import ClientError
from devflow.shared.tracker import Card

API_URL = "https://api.github.com"
API_VERSION = "2022-11-28"
DEFAULT_TIMEOUT_SECONDS = 30.0
BUG_LABEL = "bug"
BUG_TYPE = "Bug"
ISSUE_TYPE = "Issue"

# Accepts https, ssh:// and scp-like (git@github.com:owner/repo) remotes, with or without `.git`.
_GITHUB_REMOTE = re.compile(
    r"^(?:(?:https?|ssh|git)://(?:[^@/]+@)?|[^@/]+@)github\.com[/:]"
    r"(?P<owner>[^/\s]+)/(?P<name>[^/\s]+?)(?:\.git)?/?$"
)


@dataclass(frozen=True)
class GitHubRepo:
    owner: str
    name: str


def parse_github_remote(url: str) -> GitHubRepo:
    """Extracts the owner and repository name from a github.com remote URL."""
    match = _GITHUB_REMOTE.match(url.strip())
    if match is None:
        raise ClientError(f"The remote '{url}' is not a github.com repository.")
    return GitHubRepo(owner=match["owner"], name=match["name"])


class HttpGitHubClient:
    """Client for the GitHub REST API: reads an issue as a card (Bearer auth with a token)."""

    def __init__(
        self,
        repo: GitHubRepo,
        token: str,
        http_client: httpx.Client | None = None,
        timeout: float = DEFAULT_TIMEOUT_SECONDS,
    ) -> None:
        self._repo = repo
        self._headers = {
            "Authorization": f"Bearer {token}",
            "Accept": "application/vnd.github+json",
            "X-GitHub-Api-Version": API_VERSION,
        }
        self._http = http_client or httpx.Client()
        self._timeout = timeout

    def get_card(self, card_id: int) -> Card:
        url = f"{API_URL}/repos/{self._repo.owner}/{self._repo.name}/issues/{card_id}"

        try:
            response = self._http.get(url, headers=self._headers, timeout=self._timeout)
        except httpx.TimeoutException as exc:
            raise ClientError("GitHub did not respond in time.") from exc
        except httpx.HTTPError as exc:
            raise ClientError(f"Could not connect to GitHub: {exc}") from exc

        if response.status_code == 404:
            raise ClientError(
                f"Issue {card_id} does not exist in {self._repo.owner}/{self._repo.name}, "
                "or the token cannot see it."
            )
        if response.status_code in (401, 403):
            raise ClientError("GitHub rejected the credentials. Check GITHUB_TOKEN.")
        if response.status_code != 200:
            raise ClientError(f"GitHub answered with status {response.status_code}.")

        return self._parse_card(card_id, response)

    @staticmethod
    def _parse_card(card_id: int, response: httpx.Response) -> Card:
        try:
            data = response.json()
            title = data["title"]
            labels = [label["name"].lower() for label in data["labels"]]
            is_pull_request = "pull_request" in data
        except (ValueError, KeyError, TypeError) as exc:
            raise ClientError("The GitHub response does not have the expected format.") from exc

        if is_pull_request:
            raise ClientError(f"#{card_id} is a pull request, not an issue.")

        return Card(id=card_id, title=title, type=BUG_TYPE if BUG_LABEL in labels else ISSUE_TYPE)
