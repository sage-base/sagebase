"""Adapter to use sync Session with async repository.

This module provides infrastructure implementations of the domain's
ISessionAdapter port, following the Dependency Inversion Principle.
"""

from typing import Any

from sqlalchemy.engine.result import Result
from sqlalchemy.orm import Session

from src.domain.repositories.session_adapter import ISessionAdapter


class NoOpSessionAdapter(ISessionAdapter):
    """No-op session adapter for use with RepositoryAdapter.

    RepositoryAdapter handles its own transaction management
    (auto-commit per operation), so this adapter provides no-op
    implementations of all session methods.
    Use this when the underlying repository already handles commits/rollbacks.
    """

    async def execute(
        self, statement: Any, params: dict[str, Any] | None = None
    ) -> Result[Any]:
        """No-op: RepositoryAdapter handles execution."""
        raise NotImplementedError(
            "NoOpSessionAdapter does not support execute. "
            "Use repository methods instead."
        )

    async def commit(self) -> None:
        """No-op: RepositoryAdapter auto-commits."""
        pass

    async def rollback(self) -> None:
        """No-op: RepositoryAdapter handles rollback on error."""
        pass

    async def close(self) -> None:
        """No-op: RepositoryAdapter manages session lifecycle."""
        pass

    def add(self, instance: Any) -> None:
        """No-op: RepositoryAdapter handles adding."""
        pass

    def add_all(self, instances: list[Any]) -> None:
        """No-op: RepositoryAdapter handles adding."""
        pass

    async def flush(self) -> None:
        """No-op: RepositoryAdapter handles flushing."""
        pass

    async def refresh(self, instance: Any) -> None:
        """No-op: RepositoryAdapter handles refreshing."""
        pass

    async def get(self, entity_type: Any, entity_id: Any) -> Any | None:
        """No-op: Use repository.get_by_id instead."""
        raise NotImplementedError(
            "NoOpSessionAdapter does not support get. Use repository.get_by_id instead."
        )

    async def delete(self, instance: Any) -> None:
        """No-op: Use repository.delete instead."""
        pass


class AsyncSessionAdapter(ISessionAdapter):
    """Adapter that wraps sync Session to provide async interface.

    This adapter allows sync sessions to be used in async contexts,
    primarily for testing purposes. It's NOT a true async session -
    all operations are executed synchronously but exposed with async interfaces.

    Note:
        This uses composition rather than inheritance to avoid
        Liskov Substitution Principle violations.
    """

    def __init__(self, sync_session: Session):
        """Initialize with a sync session.

        Args:
            sync_session: Synchronous SQLAlchemy session to wrap
        """
        self._sync_session = sync_session

    async def execute(
        self, statement: Any, params: dict[str, Any] | None = None
    ) -> Result[Any]:
        """Execute a statement synchronously but return as if async."""
        if params:
            return self._sync_session.execute(statement, params)
        return self._sync_session.execute(statement)

    async def commit(self) -> None:
        """Commit synchronously but return as if async."""
        self._sync_session.commit()

    async def rollback(self) -> None:
        """Rollback synchronously but return as if async."""
        self._sync_session.rollback()

    async def close(self) -> None:
        """Close synchronously but return as if async."""
        self._sync_session.close()

    def add(self, instance: Any) -> None:
        """Add instance to session."""
        self._sync_session.add(instance)

    def add_all(self, instances: list[Any]) -> None:
        """Add multiple instances to session."""
        self._sync_session.add_all(instances)

    async def flush(self) -> None:
        """Flush synchronously but return as if async."""
        self._sync_session.flush()

    async def refresh(self, instance: Any) -> None:
        """Refresh instance synchronously but return as if async."""
        self._sync_session.refresh(instance)

    async def get(self, entity_type: Any, entity_id: Any) -> Any | None:
        """Get entity by primary key synchronously but return as if async."""
        return self._sync_session.get(entity_type, entity_id)

    async def delete(self, instance: Any) -> None:
        """Delete synchronously but return as if async."""
        self._sync_session.delete(instance)
