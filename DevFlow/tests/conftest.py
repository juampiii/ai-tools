from uuid import uuid4

import pytest
from langgraph.checkpoint.memory import InMemorySaver
from langgraph.graph.state import CompiledStateGraph

from devflow.shared.tracker import Card
from devflow.start_branch.graph import build_graph
from tests.fakes import FakeGitClient, FakeLlmClient, FakeTrackerClient

BASE_BRANCH = "develop"


@pytest.fixture
def tracker() -> FakeTrackerClient:
    return FakeTrackerClient(card=Card(id=12345, title="Fix login error", type="Bug"))


@pytest.fixture
def llm() -> FakeLlmClient:
    return FakeLlmClient()


@pytest.fixture
def git() -> FakeGitClient:
    return FakeGitClient()


@pytest.fixture
def graph(tracker: FakeTrackerClient, llm: FakeLlmClient, git: FakeGitClient) -> CompiledStateGraph:
    return build_graph(tracker, llm, git, InMemorySaver(), BASE_BRANCH)


@pytest.fixture
def thread_config() -> dict:
    return {"configurable": {"thread_id": str(uuid4())}}
