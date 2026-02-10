"""Adapter to bridge sync legacy code with async new implementations.

Transaction Management:
    - Single repository operations: Auto-committed individually
    - Multi-repository operations: Use transaction() context manager for atomicity

Usage Examples:
    # Single operation (auto-commits)
    repo = RepositoryAdapter(MyRepositoryImpl)
    entity = repo.get_by_id(1)

    # Multiple operations (atomic transaction)
    async with repo.transaction():
        entity1 = await repo1.create(data1)
        entity2 = await repo2.create(data2)
        # Both commit together, or rollback on error
"""

import asyncio
import logging
import threading
import types

from collections.abc import Coroutine
from contextlib import asynccontextmanager
from typing import Any, TypeVar

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.orm import Session

from src.infrastructure.config.database import DATABASE_URL


T = TypeVar("T")
logger = logging.getLogger(__name__)

# 専用バックグラウンドスレッドのevent loop（nest_asyncioの代替）
_dedicated_loop: asyncio.AbstractEventLoop | None = None
_dedicated_loop_lock = threading.Lock()


def _get_dedicated_loop() -> asyncio.AbstractEventLoop:
    """非同期処理用の専用event loopを取得する（なければ起動する）."""
    global _dedicated_loop
    with _dedicated_loop_lock:
        if _dedicated_loop is None or _dedicated_loop.is_closed():
            _dedicated_loop = asyncio.new_event_loop()
            thread = threading.Thread(
                target=_dedicated_loop.run_forever,
                daemon=True,
                name="repo-adapter-async",
            )
            thread.start()
        return _dedicated_loop


class RepositoryAdapter:
    """
    Adapter to use async repositories from sync code.

    This is a temporary bridge during migration from legacy repositories
    to new Clean Architecture implementations.
    """

    def __init__(
        self, async_repository_class: type, sync_session: Session | None = None
    ):
        """
        Initialize the adapter.

        Args:
            async_repository_class: The async repository class to adapt
            sync_session: Optional sync session (for context)
        """
        self.async_repository_class = async_repository_class
        # Cache engines per event loop to avoid asyncpg event loop errors
        self._engines: dict[int, Any] = {}
        self._session_factories: dict[int, Any] = {}
        self._shared_session: AsyncSession | None = None

    def get_async_session_factory(self):
        """Get or create an async session factory for the current event loop."""
        try:
            loop = asyncio.get_running_loop()
            loop_id = id(loop)
        except RuntimeError:
            # No running loop, use a sentinel value
            loop_id = 0

        if loop_id not in self._session_factories:
            # Convert sync database URL to async
            db_url = DATABASE_URL
            if db_url.startswith("postgresql://"):
                async_db_url = db_url.replace("postgresql://", "postgresql+asyncpg://")
            elif db_url.startswith("postgresql+psycopg2://"):
                async_db_url = db_url.replace(
                    "postgresql+psycopg2://", "postgresql+asyncpg://"
                )
            else:
                async_db_url = db_url

            engine = create_async_engine(async_db_url, echo=False)
            self._engines[loop_id] = engine
            self._session_factories[loop_id] = async_sessionmaker(
                engine, expire_on_commit=False
            )

        return self._session_factories[loop_id]

    def _run_async(self, coro: Coroutine[Any, Any, T]) -> T:
        """Run an async coroutine from sync context.

        専用バックグラウンドスレッドのevent loopでコルーチンを実行する。
        Streamlit/TornadoのメインEvent Loopには一切触れない。
        """
        try:
            loop = _get_dedicated_loop()
            future = asyncio.run_coroutine_threadsafe(coro, loop)
            return future.result()
        except Exception as e:
            logger.error(f"Failed to run async operation: {e}")
            raise

    @asynccontextmanager
    async def transaction(self):
        """
        Create a transaction context for use cases.

        Yields:
            AsyncSession: Shared session for the transaction

        Note:
            Uses SQLAlchemy's recommended pattern with session.begin()
            for proper transaction management. The transaction is automatically
            committed on success and rolled back on exception.
        """
        session_factory = self.get_async_session_factory()
        async with session_factory() as session:
            async with session.begin():
                self._shared_session = session
                logger.debug(
                    f"Transaction started, session={id(session)}, "
                    f"in_transaction={session.in_transaction()}"
                )
                try:
                    yield session
                    logger.debug(
                        f"Transaction block completed successfully, "
                        f"session={id(session)}"
                    )
                except Exception as e:
                    logger.error(
                        f"Transaction failed, will auto-rollback: {e}, "
                        f"session={id(session)}, "
                        f"in_transaction={session.in_transaction()}, "
                        f"is_active={session.is_active}"
                    )
                    raise
                finally:
                    self._shared_session = None
                    logger.debug(
                        f"Transaction context exited, session={id(session)}, "
                        f"in_transaction={session.in_transaction()}"
                    )

    def with_transaction(self, func: Any, *args: Any, **kwargs: Any) -> Any:
        """
        Execute a function within a transaction context (sync wrapper).

        This allows synchronous code (like Streamlit presenters) to use
        transactional repository operations.

        Args:
            func: Async function to execute within transaction
            *args: Positional arguments for the function
            **kwargs: Keyword arguments for the function

        Returns:
            Result of the function execution
        """

        async def transactional_wrapper() -> Any:
            async with self.transaction():
                return await func(*args, **kwargs)

        return self._run_async(transactional_wrapper())

    def __getattr__(self, name: str) -> Any:
        """
        Proxy method calls to the async repository.

        This allows the adapter to be used as if it were the repository itself.
        Returns a callable that works in both sync and async contexts.

        Note: Transaction management must be handled explicitly via
        the transaction() context manager. Repository methods only flush()
        changes; commits happen at transaction boundaries.
        """

        async def async_method(*args: Any, **kwargs: Any) -> Any:
            # Use shared session if in transaction context
            if self._shared_session is not None:
                repo = self.async_repository_class(self._shared_session)
                method = getattr(repo, name)
                return await method(*args, **kwargs)
            else:
                # Create session and auto-commit for single operations
                # Note: For multi-operation atomicity, use transaction() context
                session_factory = self.get_async_session_factory()
                async with session_factory() as session:
                    repo = self.async_repository_class(session)
                    method = getattr(repo, name)
                    result = await method(*args, **kwargs)
                    await session.commit()
                    return result

        def sync_or_async_wrapper(*args: Any, **kwargs: Any) -> Any:
            """
            Wrapper that works in both sync and async contexts.

            - When called with await: returns the coroutine directly
            - When called without await: runs synchronously via _run_async
            """
            coro = async_method(*args, **kwargs)

            # Check if we're in an async context
            import inspect

            # Get the calling frame
            frame = inspect.currentframe()
            if frame and frame.f_back and frame.f_back.f_code:
                # Check if caller is async
                caller_code = frame.f_back.f_code
                if caller_code.co_flags & inspect.CO_COROUTINE:
                    # Async context - return coroutine to be awaited
                    return coro

            # Sync context - run immediately
            return self._run_async(coro)

        return sync_or_async_wrapper

    def close(self):
        """Close all async engines."""
        for engine in self._engines.values():
            try:
                asyncio.get_running_loop()
                # イベントループ内から呼ばれた場合は専用スレッドで実行
                self._run_async(engine.dispose())
            except RuntimeError:
                # イベントループ外の場合はasyncio.runで実行
                asyncio.run(engine.dispose())
        self._engines.clear()
        self._session_factories.clear()

    def __enter__(self):
        """Context manager entry."""
        return self

    def __exit__(
        self,
        exc_type: type[BaseException] | None,
        exc_val: BaseException | None,
        exc_tb: types.TracebackType | None,
    ) -> None:
        """Context manager exit."""
        self.close()
