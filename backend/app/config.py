from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    database_url: str = "postgresql+asyncpg://pmuser:pmpass@pgbouncer:6432/pmproject"
    secret_key: str = "change-me-in-production"
    algorithm: str = "HS256"
    access_token_expire_minutes: int = 60 * 24
    # Redis
    redis_url: str = "redis://redis:6379/0"
    # Celery
    celery_broker_url: str = "redis://redis:6379/1"
    celery_result_backend: str = "redis://redis:6379/2"
    # Cache TTL (seconds)
    cache_ttl_dashboard: int = 30
    cache_ttl_reports: int = 60

    class Config:
        env_file = ".env"
        extra = "ignore"


settings = Settings()
