import pytest
from langgraph.checkpoint.memory import InMemorySaver
from langgraph.graph.state import CompiledStateGraph

from devflow.commit_message.graph import build_graph
from tests.fakes import FakeClipboardClient, FakeGitClient, FakeLlmClient, message_json


@pytest.fixture
def llm() -> FakeLlmClient:
    return FakeLlmClient([message_json("fix", "Prevent costs validation for an elearning product")])


@pytest.fixture
def git() -> FakeGitClient:
    return FakeGitClient()


@pytest.fixture
def clipboard() -> FakeClipboardClient:
    return FakeClipboardClient()


@pytest.fixture
def graph(
    llm: FakeLlmClient, git: FakeGitClient, clipboard: FakeClipboardClient
) -> CompiledStateGraph:
    return build_graph(llm, git, clipboard, InMemorySaver())
