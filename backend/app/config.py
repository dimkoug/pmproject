from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    # Database — primary (writes + general reads)
    database_url: str = "postgresql+asyncpg://pmuser:pmpass@pgbouncer:6432/pmproject"
    # Database — optional read replica; leave unset to route reads to the primary
    read_database_url: str | None = None

    secret_key: str = "change-me-in-production"
    algorithm: str = "HS256"
    access_token_expire_minutes: int = 60 * 24

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

    class Config:
        env_file = ".env"
        extra = "ignore"


settings = Settings()
