"""
Application Settings - Centralized configuration using pydantic-settings.
"""
from pydantic_settings import BaseSettings
from functools import lru_cache


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""
    
    # Server
    HOST: str = "0.0.0.0"
    PORT: int = 8000
    
    # MongoDB
    MONGO_URI: str = "mongodb://admin:admin@localhost:27017/?authSource=admin"
    MONGO_DB: str = "langchain"
    CHECKPOINT_COLLECTION: str = "checkpoints"
    SESSIONS_COLLECTION: str = "user_sessions"
    
    # OpenAI
    OPENAI_API_KEY: str = ""
    OPENAI_MODEL: str = "gpt-4o-mini"
    OPENAI_EMBEDDING_MODEL: str = "text-embedding-3-small"
    
    # JWT
    JWT_SECRET: str = "supersecret"
    
    # LangSmith (optional)
    LANGSMITH_TRACING: bool = False
    LANGSMITH_ENDPOINT: str = "https://api.smith.langchain.com"
    LANGSMITH_API_KEY: str = ""
    LANGSMITH_PROJECT: str = ""
    
    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        extra = "ignore"


@lru_cache
def get_settings() -> Settings:
    """Cached settings singleton."""
    return Settings()


# Convenience export
settings = get_settings()
