from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    app_name: str = "Quiza"
    app_env: str = "development"
    debug: bool = True
    api_v1_prefix: str = "/api/v1"

    database_url: str = "sqlite:///./quiza.db"

    jwt_secret_key: str = "change-me-dev-only-secret"
    jwt_algorithm: str = "HS256"
    access_token_expire_minutes: int = 60
    refresh_token_expire_minutes: int = 60 * 24 * 30
    password_reset_token_expire_minutes: int = 30

    openai_api_key: str | None = None
    openai_chat_model: str = "gpt-4o-mini"
    openai_embedding_model: str = "text-embedding-3-small"

    storage_backend: str = "local"
    storage_dir: str = "./storage"
    max_upload_size_mb: int = 25

    vector_store_backend: str = "sqlite"

    ai_rate_limit_per_minute: int = 10

    cors_origins: str = "http://localhost:3000"

    @property
    def cors_origin_list(self) -> list[str]:
        return [origin.strip() for origin in self.cors_origins.split(",") if origin.strip()]

    @property
    def is_production(self) -> bool:
        return self.app_env.lower() in {"production", "prod"}


@lru_cache
def get_settings() -> Settings:
    settings = Settings()
    if settings.is_production and settings.jwt_secret_key == "change-me-dev-only-secret":
        raise RuntimeError(
            "JWT_SECRET_KEY must be overridden with a real secret in production."
        )
    return settings


settings = get_settings()
