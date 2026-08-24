from typing import AsyncGenerator
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from weather_gpt.config import settings
from weather_gpt.db.base import Base


def _to_async_url(url: str) -> str:
    """Normalize a database URL to an async driver form."""
    if url.startswith("sqlite+aiosqlite"):
        return url
    if url.startswith("sqlite"):
        return url.replace("sqlite://", "sqlite+aiosqlite://", 1)
    if url.startswith("postgresql+psycopg"):
        return url
    if url.startswith("postgresql"):
        return url.replace("postgresql://", "postgresql+asyncpg://", 1)
    return url

# Create Async Engine
engine = create_async_engine(
    _to_async_url(settings.DATABASE_URL),
    echo=False,
    future=True
)

# Async Session Factory
AsyncSessionLocal = async_sessionmaker(
    bind=engine,
    class_=AsyncSession,
    expire_on_commit=False,
    autocommit=False,
    autoflush=False
)

async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """Dependency generator for FastAPI routes to obtain async DB sessions."""
    async with AsyncSessionLocal() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()

async def init_db() -> None:
    """Initialize database tables."""
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
