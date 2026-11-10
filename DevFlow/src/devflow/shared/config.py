import os
from collections.abc import Mapping
from dataclasses import dataclass

from dotenv import load_dotenv

from devflow.shared.errors import ConfigError

DEFAULT_LLM_API_URL = "http://localhost:5052/api/prompts"
DEFAULT_BASE_BRANCH = "develop"
DEFAULT_TRACKER = "ado"
REQUIRED_VARIABLES = {
    "ado": ("ADO_ORGANIZATION", "ADO_PROJECT", "ADO_PAT"),
    "github": ("GITHUB_TOKEN",),
}
SUPPORTED_TRACKERS = tuple(REQUIRED_VARIABLES)


@dataclass(frozen=True)
class AdoSettings:
    organization: str
    project: str
    pat: str


@dataclass(frozen=True)
class Settings:
    tracker: str
    llm_api_url: str
    base_branch: str
    ado: AdoSettings | None = None
    github_token: str | None = None


def load_llm_api_url(environ: Mapping[str, str] | None = None) -> str:
    """Reads LLM_API_URL (and `.env` if `environ` is not given), for graphs that need no tracker."""
    if environ is None:
        load_dotenv()
        environ = os.environ

    return environ.get("LLM_API_URL", "").strip() or DEFAULT_LLM_API_URL


def load_settings(environ: Mapping[str, str] | None = None, tracker: str | None = None) -> Settings:
    """Reads the settings from environment variables (and from `.env` if `environ` is not given).

    The tracker is the given one, or `DEFAULT_TRACKER` from the environment, or `ado`.
    Only the variables of the selected tracker are required.
    """
    if environ is None:
        load_dotenv()
        environ = os.environ

    selected = tracker or environ.get("DEFAULT_TRACKER", "").strip() or DEFAULT_TRACKER
    if selected not in SUPPORTED_TRACKERS:
        raise ConfigError(
            f"Unknown tracker '{selected}'. Supported: {', '.join(SUPPORTED_TRACKERS)}."
        )

    missing = [name for name in REQUIRED_VARIABLES[selected] if not environ.get(name, "").strip()]
    if missing:
        raise ConfigError(
            f"Missing required environment variables for tracker '{selected}': "
            f"{', '.join(missing)}. Define them in the .env file (see .env.example)."
        )

    ado = None
    github_token = None
    if selected == "ado":
        ado = AdoSettings(
            organization=environ["ADO_ORGANIZATION"].strip(),
            project=environ["ADO_PROJECT"].strip(),
            pat=environ["ADO_PAT"].strip(),
        )
    else:
        github_token = environ["GITHUB_TOKEN"].strip()

    return Settings(
        tracker=selected,
        llm_api_url=load_llm_api_url(environ),
        base_branch=environ.get("BASE_BRANCH", "").strip() or DEFAULT_BASE_BRANCH,
        ado=ado,
        github_token=github_token,
    )
