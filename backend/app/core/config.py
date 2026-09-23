from pydantic_settings import BaseSettings, SettingsConfigDict
from functools import lru_cache


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    # Database
    database_url: str = "postgresql+asyncpg://postgres:postgres@localhost:5432/lexiai"
    database_url_direct: str = ""

    # LLM
    llm_provider: str = "groq"
    groq_api_key: str = ""
    groq_model: str = "qwen/qwen3.8-27b"

    # Embeddings
    embedding_provider: str = "fastembed"
    voyage_api_key: str = ""

    # Web search
    tavily_api_key: str = ""

    # App
    frontend_origin: str = "http://localhost:5173"
    debug: bool = False


@lru_cache
def get_settings() -> Settings:
    return Settings()
