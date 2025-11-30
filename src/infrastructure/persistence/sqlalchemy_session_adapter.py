"""SQLAlchemy AsyncSession adapter for ISessionAdapter.

This module provides an adapter to wrap SQLAlchemy's AsyncSession
so it can be used with the domain's ISessionAdapter interface.
"""

from typing import Any

from sqlalchemy.engine.result import Result
from sqlalchemy.ext.asyncio import AsyncSession

from src.domain.repositories.session_adapter import ISessionAdapter


class SQLAlchemySessionAdapter(ISessionAdapter):
    """Adapter that wraps AsyncSession to provide ISessionAdapter interface.

    This adapter allows true async sessions to be used with the domain's
    ISessionAdapter port, following the Dependency Inversion Principle.
    """

    def __init__(self, async_session: AsyncSession):
        """Initialize with an async session.

        Args:
            async_session: Asynchronous SQLAlchemy session to wrap
        """
        self._session = async_session

    async def execute(
        self, statement: Any, params: dict[str, Any] | None = None
    ) -> Result[Any]:
        """Execute a statement asynchronously."""
        if params:
            return await self._session.execute(statement, params)
        return await self._session.execute(statement)

    async def commit(self) -> None:
        """Commit the current transaction."""
        await self._session.commit()

    async def rollback(self) -> None:
        """Rollback the current transaction."""
        await self._session.rollback()

    async def close(self) -> None:
        """Close the session."""
        await self._session.close()

    def add(self, instance: Any) -> None:
        """Add instance to session."""
        self._session.add(instance)

    def add_all(self, instances: list[Any]) -> None:
        """Add multiple instances to session."""
        self._session.add_all(instances)

    async def flush(self) -> None:
        """Flush changes to database."""
        await self._session.flush()

    async def refresh(self, instance: Any) -> None:
        """Refresh instance from database."""
        await self._session.refresh(instance)

    async def get(self, entity_type: Any, entity_id: Any) -> Any | None:
        """Get entity by primary key."""
        return await self._session.get(entity_type, entity_id)

    async def delete(self, instance: Any) -> None:
        """Delete instance from session."""
        await self._session.delete(instance)
