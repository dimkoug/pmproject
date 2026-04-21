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

    @property
    def effective_redis_ws_url(self) -> str:
        return self.redis_ws_url or self.redis_url

    class Config:
        env_file = ".env"
        extra = "ignore"


settings = Settings()
