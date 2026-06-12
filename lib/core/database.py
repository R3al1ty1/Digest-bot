import logging
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)

from lib.core.constants import AppEnvironment


class DatabaseManager:
    def __init__(
        self,
        dsn: str,
        environment: AppEnvironment,
        logger: logging.Logger,
    ) -> None:
        self._dsn = dsn
        self._environment = environment
        self._logger = logger
        self._engine: AsyncEngine | None = None
        self._session_factory: async_sessionmaker[AsyncSession] | None = None

    def init(self) -> None:
        if self._engine:
            return

        self._engine = create_async_engine(
            self._dsn,
            echo=(self._environment == AppEnvironment.LOCAL),
            future=True,
            pool_pre_ping=True,
        )
        self._session_factory = async_sessionmaker(
            bind=self._engine,
            autoflush=False,
            expire_on_commit=False,
            class_=AsyncSession,
        )
        self._logger.info("Database initialized successfully.")

    async def close(self) -> None:
        if self._engine:
            await self._engine.dispose()
            self._engine = None
            self._session_factory = None
            self._logger.info("Database connection closed.")

    @asynccontextmanager
    async def session(self) -> AsyncIterator[AsyncSession]:
        if not self._session_factory:
            raise RuntimeError("Database not initialized. Call init() first.")

        async with self._session_factory() as session:
            try:
                yield session
            except Exception as e:
                self._logger.error(f"DB session error, rolling back: {e}")
                await session.rollback()
                raise
            finally:
                await session.close()

    @property
    def engine(self) -> AsyncEngine:
        if not self._engine:
            raise RuntimeError("Database not initialized. Call init() first.")

        return self._engine
