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

    gemini_api_key: str | None = None
    gemini_chat_model: str = "gemini-2.5-flash"
    gemini_embedding_model: str = "gemini-embedding-001"

    storage_backend: str = "local"
    storage_dir: str = "./storage"
    max_upload_size_mb: int = 25

    supabase_url: str | None = None
    supbase_url: str | None = None
    supabase_key: str | None = None
    supabase_anon_key: str | None = None
    supabase_storage_bucket: str = "materials"

    @property
    def effective_supabase_url(self) -> str | None:
        return self.supabase_url or self.supbase_url

    @property
    def effective_supabase_key(self) -> str | None:
        return self.supabase_key or self.supabase_anon_key

    vector_store_backend: str = "sqlite"

    ai_rate_limit_per_minute: int = 10

    cors_origins: str = "http://localhost:5173,http://localhost:5174,http://localhost:3000,https://quiza-urmm.onrender.com"

    @property
    def cors_origin_list(self) -> list[str]:
        origins = []
        for raw_origin in self.cors_origins.split(","):
            origin = raw_origin.strip()
            if not origin:
                continue
            if not (origin.startswith("http://") or origin.startswith("https://")):
                if "localhost" in origin or "127.0.0.1" in origin:
                    origins.append(f"http://{origin}")
                    origins.append(f"https://{origin}")
                else:
                    origins.append(f"https://{origin}")
                    origins.append(f"http://{origin}")
            else:
                origins.append(origin)
        return origins

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
