from __future__ import annotations

from collections.abc import AsyncIterator

from sqlalchemy import text
from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)


def create_database_engine(database_url: str) -> AsyncEngine:
    return create_async_engine(database_url, pool_size=5, max_overflow=5, pool_pre_ping=True)


def create_session_factory(engine: AsyncEngine) -> async_sessionmaker[AsyncSession]:
    return async_sessionmaker(engine, expire_on_commit=False)


class DatabaseHealthChecker:
    def __init__(self, session_factory: async_sessionmaker[AsyncSession]) -> None:
        self._session_factory = session_factory

    async def check(self) -> bool:
        try:
            async with self._session_factory() as session:
                await session.execute(text("SELECT 1"))
            return True
        except Exception:
            return False


async def session_scope(
    session_factory: async_sessionmaker[AsyncSession],
) -> AsyncIterator[AsyncSession]:
    async with session_factory() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
