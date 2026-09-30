from functools import lru_cache
from pathlib import Path

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    app_name: str = Field(default="Screenshot Ingestion API", alias="APP_NAME")
    app_env: str = Field(default="dev", alias="APP_ENV")
    ingested_output_dir: str = Field(default="data/ingested", alias="INGESTED_OUTPUT_DIR")

    azure_agent_api_url: str = Field(default="", alias="AZURE_AGENT_API_URL")
    azure_agent_api_key: str = Field(default="", alias="AZURE_AGENT_API_KEY")
    azure_agent_model: str = Field(default="", alias="AZURE_AGENT_MODEL")
    azure_agent_api_version: str = Field(default="", alias="AZURE_AGENT_API_VERSION")
    agent_extraction_prompt: str = Field(
        default=(
            "Parse this screenshot and return valid JSON only. Include top-level keys: "
            "data (object), warnings (array of strings), confidence (object with "
            "overall and optional fields map)."
        ),
        alias="AGENT_EXTRACTION_PROMPT",
    )
    agent_timeout_seconds: float = Field(default=45.0, alias="AGENT_TIMEOUT_SECONDS")


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    return Settings()


settings = get_settings()


def get_ingested_output_path() -> Path:
    return Path(settings.ingested_output_dir)
