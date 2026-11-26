"""Settings, read from the environment or backend/.env."""

from functools import lru_cache
from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict

# backend/.env, wherever the server is started from.
ENV_FILE = Path(__file__).resolve().parent.parent / ".env"


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=ENV_FILE, extra="ignore")

    # "dev" prints sign-in codes to the console when RESEND_API_KEY isn't set.
    env: str = "dev"
    # Neon gives a postgresql:// URL; it's converted to the psycopg driver below.
    database_url: str = "postgresql://localhost/overloader"
    jwt_secret: str = "dev-only-change-me"
    token_days: int = 30
    resend_api_key: str | None = None
    signin_email_from: str = "Overloader <signin@example.com>"
    # Comma-separated. The Vite dev server proxies /api, so this only matters once the
    # frontend is hosted on another origin.
    cors_origins: str = ""

    @property
    def sqlalchemy_url(self) -> str:
        url = self.database_url
        for prefix in ("postgresql://", "postgres://"):
            if url.startswith(prefix):
                return "postgresql+psycopg://" + url[len(prefix) :]
        return url

    @property
    def cors_origin_list(self) -> list[str]:
        return [o.strip() for o in self.cors_origins.split(",") if o.strip()]


@lru_cache
def get_settings() -> Settings:
    return Settings()
