from functools import lru_cache

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

from app.core.errors import ConfigurationError, DatabaseConfigurationError, LLMConfigurationError


class Settings(BaseSettings):
    app_name: str = "FADUA BI Assistant"
    app_env: str = "development"
    app_host: str = "127.0.0.1"
    app_port: int = Field(default=8000, ge=1, le=65535)
    app_allowed_origins: list[str] = Field(
        default_factory=lambda: ["http://127.0.0.1:8000", "http://localhost:8000"]
    )

    openai_api_key: str | None = None
    openai_model: str = "gpt-4o-mini"
    openai_timeout_seconds: int = Field(default=20, ge=1, le=120)
    openai_max_retries: int = Field(default=2, ge=1, le=5)
    openai_retry_backoff_seconds: float = Field(default=0.75, ge=0.1, le=10.0)

    mysql_host: str | None = None
    mysql_port: int = Field(default=3306, ge=1, le=65535)
    mysql_db: str | None = None
    mysql_user: str | None = None
    mysql_password: str | None = None
    mysql_table: str = "metricas_campanas_ventas"
    mysql_connect_timeout: int = Field(default=10, ge=1, le=120)
    mysql_read_timeout: int = Field(default=10, ge=1, le=120)
    mysql_write_timeout: int = Field(default=10, ge=1, le=120)

    langfuse_public_key: str | None = None
    langfuse_secret_key: str | None = None
    langfuse_host: str = "https://cloud.langfuse.com"
    langfuse_prompt_label: str = "production"
    langfuse_prompt_cache_ttl_seconds: int = 300

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    @field_validator("app_allowed_origins", mode="before")
    @classmethod
    def split_origins(cls, value: str | list[str]) -> list[str]:
        if isinstance(value, list):
            origins = value
        else:
            origins = [origin.strip() for origin in value.split(",") if origin.strip()]

        if not origins:
            raise ValueError("APP_ALLOWED_ORIGINS must include at least one origin.")

        invalid = [origin for origin in origins if origin == "*" or not origin.startswith(("http://", "https://"))]
        if invalid:
            raise ValueError(
                "APP_ALLOWED_ORIGINS must contain explicit http(s) origins and cannot use '*'."
            )

        return origins

    def validate_runtime_configuration(self) -> None:
        missing_mysql = [
            env_name
            for env_name, value in {
                "MYSQL_HOST": self.mysql_host,
                "MYSQL_DB": self.mysql_db,
                "MYSQL_USER": self.mysql_user,
                "MYSQL_PASSWORD": self.mysql_password,
            }.items()
            if not value
        ]
        if missing_mysql:
            raise DatabaseConfigurationError(
                f"Missing required database settings: {', '.join(missing_mysql)}."
            )

        if not self.openai_api_key:
            raise LLMConfigurationError("OPENAI_API_KEY is required for the configured LLM provider.")

        if bool(self.langfuse_public_key) != bool(self.langfuse_secret_key):
            raise ConfigurationError(
                "LANGFUSE_PUBLIC_KEY and LANGFUSE_SECRET_KEY must be configured together."
            )


@lru_cache
def get_settings() -> Settings:
    return Settings()
