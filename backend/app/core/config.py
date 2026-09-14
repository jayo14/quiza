from functools import lru_cache

from pathlib import Path
from pydantic_settings import BaseSettings, SettingsConfigDict

_backend_dir = Path(__file__).resolve().parents[2]
_env_candidates = (
    ".env",
    "backend/.env",
    str(_backend_dir / ".env"),
)


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=_env_candidates, env_file_encoding="utf-8", extra="ignore")

    app_name: str = "Quiza"
    app_env: str = "development"
    debug: bool = False
    api_v1_prefix: str = "/api/v1"

    database_url: str = "sqlite:///./quiza.db"

    jwt_secret_key: str = "change-me-dev-only-secret"
    jwt_algorithm: str = "HS256"
    access_token_expire_minutes: int = 60
    refresh_token_expire_minutes: int = 60 * 24 * 30
    password_reset_token_expire_minutes: int = 30

    # Gemini
    gemini_api_key: str | None = None
    gemini_chat_model: str = "gemini-3.6-flash"
    gemini_fallback_models: str = "gemini-2.5-flash,gemini-1.5-flash,gemini-2.5-pro"
    gemini_embedding_model: str = "text-embedding-004"
    gemini_embedding_fallback_models: str = "gemini-embedding-001,gemini-embedding-2"

    # OpenAI
    openai_api_key: str | None = None
    openai_base_url: str | None = None
    openai_chat_model: str = "gpt-4o-mini"
    openai_fallback_models: str = "gpt-4o-mini,gpt-4o"

    # NVIDIA BUILD NIM
    nvidia_api_key: str | None = None
    nvidia_base_url: str = "https://integrate.api.nvidia.com/v1"
    nvidia_chat_model: str = "meta/llama-3.3-70b-instruct"
    nvidia_fallback_models: str = "meta/llama-3.3-70b-instruct,mistralai/mistral-large-2-instruct,deepseek-ai/deepseek-r1"

    # Provider failover chain & health management
    llm_provider_priority: str = "gemini,openai,nvidia"
    llm_model_cooldown_seconds: int = 60

    storage_backend: str = "supabase"
    storage_dir: str = "./storage"
    max_upload_size_mb: int = 25

    supabase_url: str | None = None
    supbase_url: str | None = None  # Legacy typo fallback; use supabase_url instead
    supabase_key: str | None = None
    supabase_anon_key: str | None = None
    supabase_storage_bucket: str = "materials"

    @property
    def effective_jwt_secret(self) -> str:
        if self.is_production and self.jwt_secret_key == "change-me-dev-only-secret":
            import logging
            logging.getLogger(__name__).critical(
                "JWT_SECRET_KEY is set to the default dev value in production! "
                "Set JWT_SECRET_KEY to a strong random string."
            )
        return self.jwt_secret_key

    @property
    def effective_supabase_url(self) -> str | None:
        return self.supabase_url or self.supbase_url

    @property
    def effective_supabase_key(self) -> str | None:
        return self.supabase_key or self.supabase_anon_key

    vector_store_backend: str = "pgvector"

    ai_rate_limit_per_minute: int = 10
    # SMTP Settings
    smtp_server: str = "smtp.gmail.com"
    smtp_port: int = 587
    smtp_username: str | None = None
    smtp_password: str | None = None
    smtp_from_email: str | None = None
    smtp_from_name: str = "Quiza"

    frontend_url: str = "http://localhost:5173"

    # Celery / Redis
    redis_url: str = "redis://localhost:6379/0"
    auto_start_celery: bool = False


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
    import logging
    _logger = logging.getLogger(__name__)
    settings = Settings()
    if settings.is_production and settings.jwt_secret_key == "change-me-dev-only-secret":
        raise RuntimeError(
            "JWT_SECRET_KEY must be overridden with a real secret in production."
        )
    if not settings.gemini_api_key and not settings.openai_api_key and not settings.nvidia_api_key:
        _logger.warning("No LLM API keys configured (gemini, openai, nvidia). AI features will fail.")
    return settings


settings = get_settings()
