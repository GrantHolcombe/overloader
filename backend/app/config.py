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
    # Max custom exercises per user; unset means no limit. The Pro plan will set this per plan
    # (free: 5); until billing exists everyone is unlimited.
    custom_exercise_limit: int | None = None
    resend_api_key: str | None = None
    signin_email_from: str = "Overloader <signin@example.com>"
    # Comma-separated. The Vite dev server proxies /api, so this only matters once the
    # frontend is hosted on another origin.
    cors_origins: str = ""
    # Behind Cloudflare the TCP peer isn't the user, so the per-IP sign-in rate limit reads the
    # client address from this header (Cloudflare sets cf-connecting-ip itself). Falls back to
    # the connection's address when unset or missing.
    client_ip_header: str | None = None
    # When set, every request except /api/health must carry this value in the X-Origin-Verify
    # header. Cloudflare adds it, so calling the Lambda Function URL directly gets a 403 and the
    # client IP header above can't be forged by skipping Cloudflare.
    origin_secret: str | None = None

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
