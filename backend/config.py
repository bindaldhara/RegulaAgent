from functools import lru_cache
from urllib.parse import quote_plus, urlparse

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    # mock | jev | openrouter | auto — see docs/intent.md
    agent_provider: str = "auto"

    typesafe_api_key: str | None = None
    typesafe_model: str = "jev-latest"
    # JEV on OpenRouter (System One API); see https://openrouter.ai/~typesafe/jev-latest
    openrouter_jev_model: str = "~typesafe/jev-latest"

    supabase_url: str = ""
    supabase_jwt_secret: str = ""

    openrouter_api_key: str | None = None
    openrouter_model: str = "openai/gpt-4o-mini"
    openrouter_base_url: str = "https://openrouter.ai/api/v1"
    openrouter_app_url: str = "http://localhost:5173"
    # Intent OpenRouter chat calls (structured output); avoid infinite hang on slow models
    intent_openrouter_timeout_seconds: float = 45.0

    # G-Eval judge (defaults to openrouter_model). Prefer a paid mini model over :free for JSON scoring.
    eval_judge_model: str | None = None

    livekit_url: str = ""
    livekit_api_key: str = ""
    livekit_api_secret: str = ""
    livekit_agent_name: str = "regula-voice"

    # Optional single URI. If password contains +, @, /, etc., use POSTGRES_* below instead.
    database_url: str | None = None

    postgres_host: str = "localhost"
    postgres_port: int = 5432
    postgres_db: str = "regula_agent"
    postgres_user: str = "regula"
    postgres_password: str = "regula"

    @staticmethod
    def _normalize_database_url(url: str) -> str:
        if url.startswith("postgres://"):
            return "postgresql://" + url[len("postgres://") :]
        return url

    @staticmethod
    def _looks_like_valid_postgres_url(url: str) -> bool:
        parsed = urlparse(url)
        if not parsed.hostname or "." not in parsed.hostname:
            return False
        if "@" in (parsed.path or ""):
            return False
        return parsed.scheme in ("postgresql", "postgres")

    def _url_from_postgres_fields(self) -> str:
        user = quote_plus(self.postgres_user)
        password = quote_plus(self.postgres_password)
        return (
            f"postgresql://{user}:{password}"
            f"@{self.postgres_host}:{self.postgres_port}/{self.postgres_db}"
        )

    @property
    def resolved_database_url(self) -> str:
        if self.database_url and self.database_url.strip():
            url = self._normalize_database_url(self.database_url.strip())
            if self._looks_like_valid_postgres_url(url):
                return url
        return self._url_from_postgres_fields()

    @property
    def supabase_configured(self) -> bool:
        return bool(self.supabase_url.strip())

    @property
    def livekit_configured(self) -> bool:
        return bool(
            self.livekit_url.strip()
            and self.livekit_api_key.strip()
            and self.livekit_api_secret.strip()
        )


@lru_cache
def get_settings() -> Settings:
    return Settings()
