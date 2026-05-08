from functools import lru_cache
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    app_name: str = "Mindly Memory Agent"
    log_level: str = "INFO"
    openrouter_api_key: str | None = None
    openrouter_model: str = "google/gemini-2.5-flash-lite"
    openrouter_fallback_models: str = "openai/gpt-4o-mini,openai/gpt-4.1-mini"
    openrouter_base_url: str = "https://openrouter.ai/api/v1"
    openrouter_referer: str = "http://127.0.0.1:8000"
    openrouter_app_title: str = "Mindly Memory Agent"
    use_fake_llm: bool = False
    history_window: int = 8
    chat_history_backend: str = "memory"
    chat_history_max_messages: int = 0
    database_url: str = "postgresql://mindly:mindly@127.0.0.1:5432/mindly"
    memory_backend: str = "fact"
    mempalace_path: str = "data/mempalace"
    mempalace_collection: str = "mindly_memory_facts"
    fact_extractor: str = "llm"

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8")


@lru_cache
def get_settings() -> Settings:
    return Settings()