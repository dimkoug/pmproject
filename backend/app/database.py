from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.orm import DeclarativeBase
from sqlalchemy.pool import NullPool

from app.config import settings

# When using PgBouncer in transaction mode, disable SQLAlchemy's internal pool
# because PgBouncer handles connection pooling at the proxy layer.
# Use NullPool so each request gets a fresh connection from PgBouncer.
_use_pgbouncer = "pgbouncer" in settings.database_url

engine = create_async_engine(
    settings.database_url,
    echo=False,
    # NullPool when behind PgBouncer; standard pool for direct Postgres / tests
    **({"poolclass": NullPool} if _use_pgbouncer else {
        "pool_size": 20,
        "max_overflow": 10,
        "pool_recycle": 3600,
        "pool_pre_ping": True,
    }),
    # PgBouncer transaction mode doesn't support prepared statements
    connect_args={"prepared_statement_cache_size": 0} if _use_pgbouncer else {},
)
async_session = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)


class Base(DeclarativeBase):
    pass


async def get_db() -> AsyncSession:
    async with async_session() as session:
        yield session
