from functools import lru_cache
from pathlib import Path

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    app_name: str = Field(default="Hard9Stats MLB Playoffs API", alias="APP_NAME")
    app_env: str = Field(default="dev", alias="APP_ENV")
    ollama_base_url: str = Field(default="http://localhost:11434", alias="OLLAMA_BASE_URL")
    ollama_model: str = Field(default="gemma4:26b", alias="OLLAMA_MODEL")
    agent_timeout_seconds: float = Field(default=45.0, alias="AGENT_TIMEOUT_SECONDS")


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    return Settings()


settings = get_settings()


def get_llm_prompt_path(filename: str) -> Path:
    return Path(__file__).resolve().parents[2] / "data" / "llm-prompts" / filename
