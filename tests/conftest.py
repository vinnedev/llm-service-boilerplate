import os
import pytest
from datetime import datetime, timezone
from unittest.mock import MagicMock, AsyncMock, patch
from typing import Generator, AsyncGenerator
import secrets

os.environ.setdefault("OPENAI_API_KEY", "test-key")
os.environ.setdefault("MONGO_URI", "mongodb://localhost:27017")
os.environ.setdefault("MONGO_DB", "test_db")

from fastapi.testclient import TestClient
from httpx import AsyncClient, ASGITransport

from shared.models.users_model import UsersModel
from shared.models.sessions_model import SessionsModel, SessionCreate, SessionResponse


@pytest.fixture
def mock_mongo_collection() -> MagicMock:
    collection = MagicMock()
    collection.find_one = MagicMock(return_value=None)
    collection.insert_one = MagicMock()
    collection.find = MagicMock(return_value=iter([]))
    collection.find_one_and_update = MagicMock(return_value=None)
    collection.delete_one = MagicMock(return_value=MagicMock(deleted_count=0))
    return collection


@pytest.fixture
def mock_mongo_client() -> MagicMock:
    client = MagicMock()
    client.admin.command = MagicMock(return_value={"ok": 1})
    return client


@pytest.fixture
def sample_user() -> UsersModel:
    now = datetime.now(timezone.utc)
    return UsersModel(
        user_id="user_123",
        name="Test User",
        email="test@example.com",
        created_at=now,
        updated_at=now,
    )


@pytest.fixture
def sample_user_doc(sample_user: UsersModel) -> dict:
    return {
        "_id": sample_user.user_id,
        "user_id": sample_user.user_id,
        "name": sample_user.name,
        "email": sample_user.email,
        "password": "hashed_password",
        "created_at": sample_user.created_at,
        "updated_at": sample_user.updated_at,
    }


@pytest.fixture
def sample_session() -> SessionsModel:
    now = datetime.now(timezone.utc)
    session_id = "session_456"
    return SessionsModel(
        session_id=session_id,
        thread_id=session_id,
        user_id="user_123",
        name="Test Session",
        created_at=now,
        updated_at=now,
    )


@pytest.fixture
def sample_session_doc(sample_session: SessionsModel) -> dict:
    return sample_session.to_document()


@pytest.fixture
def sample_session_create() -> SessionCreate:
    return SessionCreate(user_id="user_123", name="New Session")


@pytest.fixture
def mock_checkpointer() -> MagicMock:
    checkpointer = MagicMock()
    checkpointer.get_tuple = MagicMock(return_value=None)
    checkpointer.put = MagicMock()
    return checkpointer


@pytest.fixture
def mock_openai_response() -> str:
    return "This is a test response from the AI."


@pytest.fixture
def mock_conversation_agent(mock_checkpointer: MagicMock, mock_openai_response: str):
    with patch("modules.langchain.agents.conversation_agent.ChatOpenAI"):
        with patch("modules.langchain.agents.conversation_agent.create_agent") as mock_create:
            mock_agent = MagicMock()

            async def mock_stream(*args, **kwargs):
                for chunk in mock_openai_response.split():
                    yield chunk + " "

            mock_agent.astream_events = AsyncMock(return_value=mock_stream())
            mock_agent.ainvoke = AsyncMock(return_value={
                "messages": [MagicMock(content=mock_openai_response)]
            })
            mock_create.return_value = mock_agent

            from modules.langchain.agents.conversation_agent import ConversationAgent
            agent = ConversationAgent(mock_checkpointer)
            yield agent


@pytest.fixture
def auth_token() -> str:
    return secrets.token_urlsafe(32)


@pytest.fixture
def auth_session_doc(auth_token: str, sample_user: UsersModel) -> dict:
    now = datetime.now(timezone.utc)
    from datetime import timedelta
    return {
        "token": auth_token,
        "user_id": sample_user.user_id,
        "created_at": now,
        "expires_at": now + timedelta(days=7),
    }


class MockCursor:
    def __init__(self, data: list):
        self._data = data
        self._sorted = False

    def sort(self, field: str, direction: int):
        self._sorted = True
        return self

    def __iter__(self):
        return iter(self._data)


def create_mock_find(data: list):
    def mock_find(*args, **kwargs):
        return MockCursor(data)
    return mock_find
