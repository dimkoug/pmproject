from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.orm import DeclarativeBase
from sqlalchemy.pool import NullPool

from app.config import settings


def _engine_kwargs(url: str) -> dict:
    """Engine kwargs — NullPool when behind PgBouncer (it pools for us)."""
    use_pgbouncer = "pgbouncer" in url
    return {
        **({"poolclass": NullPool} if use_pgbouncer else {
            "pool_size": 20,
            "max_overflow": 10,
            "pool_recycle": 3600,
            "pool_pre_ping": True,
        }),
        # PgBouncer transaction mode doesn't support prepared statements
        "connect_args": {"prepared_statement_cache_size": 0} if use_pgbouncer else {},
    }


# Primary engine — writes and general reads
engine = create_async_engine(settings.database_url, echo=False, **_engine_kwargs(settings.database_url))
async_session = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

# Read-only engine — backs the read replica when configured; otherwise falls
# back to the primary so `get_read_db` is always callable.
_read_url = settings.read_database_url or settings.database_url
read_engine = (
    create_async_engine(_read_url, echo=False, **_engine_kwargs(_read_url))
    if settings.read_database_url
    else engine
)
read_async_session = (
    async_sessionmaker(read_engine, class_=AsyncSession, expire_on_commit=False)
    if settings.read_database_url
    else async_session
)


class Base(DeclarativeBase):
    pass


async def get_db() -> AsyncSession:
    async with async_session() as session:
        yield session


async def get_read_db() -> AsyncSession:
    """Read-only session — use for heavy analytics endpoints (dashboards,
    P&L, Balance Sheet, Cash Flow, portfolio, activity log). Falls back to the
    primary when no replica is configured, so endpoints can depend on this
    unconditionally.
    """
    async with read_async_session() as session:
        yield session
