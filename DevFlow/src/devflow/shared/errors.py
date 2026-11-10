class ClientError(Exception):
    """Failure of an external client (ADO, LLM, git) with a message ready to show to the user."""


class ConfigError(Exception):
    """Missing or invalid configuration, with a message ready to show to the user."""
