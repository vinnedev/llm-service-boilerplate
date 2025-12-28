import os
import pytest
from typing import Generator
from testcontainers.mongodb import MongoDbContainer
from pymongo import MongoClient

os.environ.setdefault("OPENAI_API_KEY", "test-key-integration")


@pytest.fixture(scope="session")
def mongodb_container() -> Generator[MongoDbContainer, None, None]:
    container = MongoDbContainer("mongo:7.0")
    container.start()
    yield container
    container.stop()


@pytest.fixture(scope="session")
def mongodb_uri(mongodb_container: MongoDbContainer) -> str:
    return mongodb_container.get_connection_url()


@pytest.fixture(scope="session")
def mongodb_client(mongodb_uri: str) -> Generator[MongoClient, None, None]:
    client = MongoClient(mongodb_uri)
    yield client
    client.close()


@pytest.fixture
def test_database(mongodb_client: MongoClient):
    db_name = "test_llm_service"
    db = mongodb_client[db_name]
    yield db
    mongodb_client.drop_database(db_name)


@pytest.fixture
def users_collection(test_database):
    return test_database["users"]


@pytest.fixture
def sessions_collection(test_database):
    return test_database["user_sessions"]


@pytest.fixture
def auth_sessions_collection(test_database):
    return test_database["auth_sessions"]


@pytest.fixture
def checkpoints_collection(test_database):
    return test_database["checkpoints"]


@pytest.fixture
def integration_settings(mongodb_uri: str, test_database):
    from config import settings as settings_module
    from config.settings import get_settings

    get_settings.cache_clear()
    original_get_settings = settings_module.get_settings

    class TestSettings:
        MONGO_URI = mongodb_uri
        MONGO_DB = test_database.name
        SESSIONS_COLLECTION = "user_sessions"
        CHECKPOINT_COLLECTION = "checkpoints"
        OPENAI_API_KEY = "test-key"
        OPENAI_MODEL = "gpt-4o-mini"
        OPENAI_EMBEDDING_MODEL = "text-embedding-3-small"
        JWT_SECRET = "test-secret"
        HOST = "0.0.0.0"
        PORT = 8000
        LANGSMITH_TRACING = False
        LANGSMITH_ENDPOINT = ""
        LANGSMITH_API_KEY = ""
        LANGSMITH_PROJECT = ""

    yield TestSettings()

    get_settings.cache_clear()
