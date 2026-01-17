"""Async database configuration and session management."""

import asyncio

from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager
from typing import ClassVar

from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)

from src.infrastructure.config.settings import settings


class AsyncDatabase:
    """Async database manager.

    イベントループごとにエンジンを管理することで、Streamlitなどの
    異なるイベントループでリクエストが実行される環境でも安全に動作します。
    """

    # イベントループごとのエンジンをキャッシュ
    _engines: ClassVar[dict[int, AsyncEngine]] = {}
    _session_makers: ClassVar[dict[int, async_sessionmaker[AsyncSession]]] = {}

    def __init__(self):
        """Initialize async database manager."""
        # Convert sync database URL to async
        database_url = settings.get_database_url()
        # Replace postgresql:// with postgresql+asyncpg://
        if database_url.startswith("postgresql://"):
            self._async_url = database_url.replace(
                "postgresql://", "postgresql+asyncpg://"
            )
        else:
            self._async_url = database_url

    def _get_engine_and_session_maker(
        self,
    ) -> tuple[AsyncEngine, async_sessionmaker[AsyncSession]]:
        """現在のイベントループに対応するエンジンとセッションメーカーを取得する。

        イベントループごとにエンジンをキャッシュすることで、
        異なるイベントループからの呼び出しでも安全に動作します。
        """
        try:
            loop = asyncio.get_running_loop()
            loop_id = id(loop)
        except RuntimeError:
            # イベントループが存在しない場合は0をIDとして使用
            loop_id = 0

        if loop_id not in self._engines:
            engine = create_async_engine(self._async_url, echo=False)
            session_maker = async_sessionmaker(
                engine, class_=AsyncSession, expire_on_commit=False
            )
            self._engines[loop_id] = engine
            self._session_makers[loop_id] = session_maker

        return self._engines[loop_id], self._session_makers[loop_id]

    @property
    def engine(self) -> AsyncEngine:
        """現在のイベントループに対応するエンジンを取得する。"""
        engine, _ = self._get_engine_and_session_maker()
        return engine

    @property
    def async_session_maker(self) -> async_sessionmaker[AsyncSession]:
        """現在のイベントループに対応するセッションメーカーを取得する。"""
        _, session_maker = self._get_engine_and_session_maker()
        return session_maker

    @asynccontextmanager
    async def get_session(self) -> AsyncGenerator[AsyncSession]:
        """Get an async database session.

        Yields:
            AsyncSession: Database session
        """
        async with self.async_session_maker() as session:
            try:
                yield session
                await session.commit()
            except Exception:
                await session.rollback()
                raise
            finally:
                await session.close()

    @asynccontextmanager
    async def get_session_autocommit(self) -> AsyncGenerator[AsyncSession]:
        """Get an async database session with autocommit behavior.

        Each operation commits immediately, useful for batch operations
        where individual failures shouldn't affect others.

        Yields:
            AsyncSession: Database session with autocommit
        """
        async with self.async_session_maker() as session:
            try:
                yield session
                # Don't auto-commit here, let caller manage
            except Exception:
                await session.rollback()
                raise
            finally:
                await session.close()


# Global instance
async_db = AsyncDatabase()


# Convenience function for backward compatibility
@asynccontextmanager
async def get_async_session() -> AsyncGenerator[AsyncSession]:
    """Get an async database session.

    Yields:
        AsyncSession: Database session
    """
    async with async_db.get_session() as session:
        yield session
