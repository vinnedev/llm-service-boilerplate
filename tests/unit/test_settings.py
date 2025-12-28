import pytest
import os
from unittest.mock import patch


pytestmark = pytest.mark.unit


class TestSettings:
    @pytest.fixture(autouse=True)
    def clear_cache(self):
        from config.settings import get_settings
        get_settings.cache_clear()
        yield
        get_settings.cache_clear()

    def test_default_values(self):
        env_override = {
            "HOST": "",
            "PORT": "",
            "MONGO_DB": "",
            "OPENAI_MODEL": "",
            "JWT_SECRET": "",
        }
        with patch.dict(os.environ, env_override, clear=False):
            from config.settings import Settings

            default_settings = Settings(
                HOST="0.0.0.0",
                PORT=8000,
                MONGO_DB="langchain",
                CHECKPOINT_COLLECTION="checkpoints",
                SESSIONS_COLLECTION="user_sessions",
                OPENAI_MODEL="gpt-4o-mini",
                JWT_SECRET="supersecret",
                LANGSMITH_TRACING=False,
            )

            assert default_settings.HOST == "0.0.0.0"
            assert default_settings.PORT == 8000
            assert default_settings.MONGO_DB == "langchain"
            assert default_settings.CHECKPOINT_COLLECTION == "checkpoints"
            assert default_settings.SESSIONS_COLLECTION == "user_sessions"
            assert default_settings.OPENAI_MODEL == "gpt-4o-mini"
            assert default_settings.JWT_SECRET == "supersecret"
            assert default_settings.LANGSMITH_TRACING is False

    def test_env_override(self):
        env_vars = {
            "HOST": "127.0.0.1",
            "PORT": "9000",
            "MONGO_URI": "mongodb://custom:27017",
            "MONGO_DB": "custom_db",
            "OPENAI_API_KEY": "test-key",
            "JWT_SECRET": "custom-secret",
        }

        with patch.dict(os.environ, env_vars, clear=False):
            from config.settings import Settings
            settings = Settings()

            assert settings.HOST == "127.0.0.1"
            assert settings.PORT == 9000
            assert settings.MONGO_URI == "mongodb://custom:27017"
            assert settings.MONGO_DB == "custom_db"
            assert settings.OPENAI_API_KEY == "test-key"
            assert settings.JWT_SECRET == "custom-secret"

    def test_get_settings_cached(self):
        from config.settings import get_settings

        settings1 = get_settings()
        settings2 = get_settings()

        assert settings1 is settings2

    def test_langsmith_settings(self):
        env_vars = {
            "LANGSMITH_TRACING": "True",
            "LANGSMITH_API_KEY": "ls-key",
            "LANGSMITH_PROJECT": "test-project",
        }

        with patch.dict(os.environ, env_vars, clear=False):
            from config.settings import Settings
            settings = Settings()

            assert settings.LANGSMITH_TRACING is True
            assert settings.LANGSMITH_API_KEY == "ls-key"
            assert settings.LANGSMITH_PROJECT == "test-project"
