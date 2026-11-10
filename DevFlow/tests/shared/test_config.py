import pytest

from devflow.shared.config import load_llm_api_url, load_settings
from devflow.shared.errors import ConfigError

ADO_ENV = {"ADO_ORGANIZATION": "org", "ADO_PROJECT": "proj", "ADO_PAT": "secret"}
GITHUB_ENV = {"GITHUB_TOKEN": "gh-secret"}


def test_load_settings_applies_defaults_for_optional_variables():
    settings = load_settings(ADO_ENV)

    assert settings.llm_api_url == "http://localhost:5052/api/prompts"
    assert settings.base_branch == "develop"


def test_load_settings_defaults_to_the_ado_tracker():
    settings = load_settings(ADO_ENV)

    assert settings.tracker == "ado"


def test_load_settings_reads_all_ado_values():
    environ = {**ADO_ENV, "LLM_API_URL": "http://llm.test/api", "BASE_BRANCH": "main"}

    settings = load_settings(environ)

    assert settings.ado is not None
    assert settings.ado.organization == "org"
    assert settings.ado.project == "proj"
    assert settings.ado.pat == "secret"
    assert settings.github_token is None
    assert settings.llm_api_url == "http://llm.test/api"
    assert settings.base_branch == "main"


def test_load_settings_lists_every_missing_ado_variable():
    with pytest.raises(ConfigError) as exc_info:
        load_settings({"ADO_ORGANIZATION": "org"})

    message = str(exc_info.value)
    assert "ADO_PROJECT" in message
    assert "ADO_PAT" in message
    assert "ADO_ORGANIZATION" not in message


def test_load_settings_treats_blank_required_variable_as_missing():
    with pytest.raises(ConfigError, match="ADO_PAT"):
        load_settings({**ADO_ENV, "ADO_PAT": "   "})


def test_load_settings_reads_the_github_token_when_the_tracker_is_github():
    settings = load_settings(GITHUB_ENV, tracker="github")

    assert settings.tracker == "github"
    assert settings.github_token == "gh-secret"
    assert settings.ado is None


def test_load_settings_does_not_require_ado_variables_for_github():
    settings = load_settings(GITHUB_ENV, tracker="github")

    assert settings.tracker == "github"


def test_load_settings_requires_the_github_token_for_github():
    with pytest.raises(ConfigError, match="GITHUB_TOKEN"):
        load_settings(ADO_ENV, tracker="github")


def test_load_settings_does_not_require_the_github_token_for_ado():
    settings = load_settings(ADO_ENV, tracker="ado")

    assert settings.github_token is None


def test_load_settings_uses_default_tracker_from_the_environment():
    settings = load_settings({**GITHUB_ENV, "DEFAULT_TRACKER": "github"})

    assert settings.tracker == "github"


def test_load_settings_explicit_tracker_overrides_the_default_tracker_variable():
    environ = {**ADO_ENV, **GITHUB_ENV, "DEFAULT_TRACKER": "github"}

    settings = load_settings(environ, tracker="ado")

    assert settings.tracker == "ado"


def test_load_settings_rejects_an_unknown_default_tracker():
    with pytest.raises(ConfigError, match="jira"):
        load_settings({**ADO_ENV, "DEFAULT_TRACKER": "jira"})


def test_load_llm_api_url_defaults_without_requiring_any_tracker_variable():
    assert load_llm_api_url({}) == "http://localhost:5052/api/prompts"


def test_load_llm_api_url_reads_the_environment_variable():
    assert load_llm_api_url({"LLM_API_URL": " http://llm.test/api "}) == "http://llm.test/api"
