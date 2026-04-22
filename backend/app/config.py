"""Environment-driven application settings.

Populated via `.env` + real env vars through pydantic-settings. Three rules
worth remembering when adding a new field:

  1. Add a sensible dev-friendly default so local runs don't need extra
     plumbing. When there is no safe default (secrets, API keys), use
     `None` and guard the feature at call sites.
  2. Never read raw `os.environ` at import time — add a `Settings` field so
     every config value is visible in one place and can be overridden in
     tests.
  3. For fields that can leak sensitive state (SECRET_KEY, Stripe secrets),
     add a validator that refuses to boot in `APP_ENV=production` when the
     value is still the dev default.

`effective_redis_ws_url` / `effective_cors_origins` are computed properties
so consumers get a single authoritative value without repeating the
fallback logic.
"""
import os

from pydantic_settings import BaseSettings


# Sentinel used as the dev default for SECRET_KEY. A production-mode startup
# with this value refuses to boot so nobody ships a forgeable JWT signing key.
_DEV_SECRET = "change-me-in-production"


class Settings(BaseSettings):
    # Database — primary (writes + general reads)
    database_url: str = "postgresql+asyncpg://pmuser:pmpass@pgbouncer:6432/pmproject"
    # Database — optional read replica; leave unset to route reads to the primary
    read_database_url: str | None = None

    # JWT signing key. In production, `.env` MUST set SECRET_KEY to a random
    # high-entropy string. See the startup guard in `_validate_secret_key()`.
    secret_key: str = _DEV_SECRET
    algorithm: str = "HS256"
    access_token_expire_minutes: int = 60 * 24

    # Deployment environment — "production" triggers strict config validation
    # at import time. Any other value (dev / ci / test) allows the dev default
    # so local/CI runs don't need a real secret.
    app_env: str = "development"
    # CORS — comma-separated allow-list of origins (scheme + host + optional
    # port). Production deployments must set this explicitly; an empty string
    # falls back to app_base_url only. Wildcard "*" is still permitted for
    # dev but is incompatible with allow_credentials (the HTTP spec rejects
    # it) — main.py enforces that constraint.
    cors_origins: str = ""

    # Redis — split across three instances. Defaults keep backward compat
    # with a single Redis by falling through to redis_url when the specialised
    # URL is not set.
    redis_url: str = "redis://redis-cache:6379/0"
    redis_ws_url: str | None = None  # WebSocket pub/sub; defaults to redis_url
    # Celery
    celery_broker_url: str = "redis://redis-broker:6379/0"
    celery_result_backend: str = "redis://redis-broker:6379/1"
    # Cache TTL (seconds)
    cache_ttl_dashboard: int = 30
    cache_ttl_reports: int = 60

    # Email delivery (SMTP)
    smtp_host: str | None = None
    smtp_port: int = 587
    smtp_user: str | None = None
    smtp_password: str | None = None
    smtp_tls: bool = True
    email_from: str = "PM Project <no-reply@pmproject.dev>"
    app_base_url: str = "http://localhost"

    # SMS delivery (Twilio)
    sms_enabled: bool = False
    twilio_account_sid: str | None = None
    twilio_auth_token: str | None = None
    twilio_from: str | None = None  # the "From" phone number, e.g. "+15551234567"

    # Stripe (#80) — set the key to enable "Pay invoice" buttons.
    stripe_secret_key: str | None = None
    stripe_webhook_secret: str | None = None
    stripe_currency_default: str = "usd"

    # LLM (#52) — OpenAI-compatible chat-completions API.
    # When llm_api_key is unset, the planner falls back to a heuristic mock so
    # the feature stays demoable without API credits.
    llm_api_key: str | None = None
    llm_base_url: str = "https://api.openai.com/v1"
    llm_model: str = "gpt-4o-mini"
    llm_timeout_seconds: int = 60

    # Production ops
    sentry_dsn: str | None = None                       # unset → skip Sentry init
    sentry_environment: str = "production"
    sentry_traces_sample_rate: float = 0.0              # opt-in to perf monitoring
    per_user_rate_limit_rpm: int = 600                  # requests/minute/user
    audit_retention_days: int = 365
    backup_retention_days: int = 30
    backup_dir: str = "/app/backups"                    # nightly pg_dumps land here

    @property
    def effective_redis_ws_url(self) -> str:
        return self.redis_ws_url or self.redis_url

    @property
    def effective_cors_origins(self) -> list[str]:
        """Parsed CORS allow-list. Falls back to app_base_url when the
        explicit env var is empty. Empty string entries are dropped."""
        raw = self.cors_origins.strip() if self.cors_origins else ""
        if raw:
            return [o.strip() for o in raw.split(",") if o.strip()]
        return [self.app_base_url] if self.app_base_url else []

    class Config:
        env_file = ".env"
        extra = "ignore"


def _validate_secret_key(s: "Settings") -> None:
    """Refuse to boot in production with the placeholder secret. Dev/CI envs
    may use the default so local runs don't need `.env` plumbing."""
    if s.app_env.lower() == "production" and s.secret_key == _DEV_SECRET:
        raise RuntimeError(
            "SECRET_KEY is unset (still the dev placeholder) while APP_ENV=production. "
            "Generate a random secret and set SECRET_KEY in the environment."
        )


settings = Settings()
_validate_secret_key(settings)
