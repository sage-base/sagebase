"""Election member repository implementation using SQLAlchemy."""

import logging

from datetime import datetime
from typing import Any

from pydantic import BaseModel as PydanticBaseModel
from sqlalchemy import text
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.ext.asyncio import AsyncSession

from src.domain.entities.election_member import ElectionMember
from src.domain.repositories.election_member_repository import ElectionMemberRepository
from src.domain.repositories.session_adapter import ISessionAdapter
from src.infrastructure.exceptions import (
    DatabaseError,
    UpdateError,
)
from src.infrastructure.persistence.base_repository_impl import BaseRepositoryImpl


logger = logging.getLogger(__name__)


class ElectionMemberModel(PydanticBaseModel):
    """Election member database model."""

    id: int | None = None
    election_id: int
    politician_id: int
    result: str
    votes: int | None = None
    rank: int | None = None
    created_at: datetime | None = None
    updated_at: datetime | None = None

    class Config:
        arbitrary_types_allowed = True


class ElectionMemberRepositoryImpl(
    BaseRepositoryImpl[ElectionMember], ElectionMemberRepository
):
    """Election member repository implementation using SQLAlchemy."""

    def __init__(self, session: AsyncSession | ISessionAdapter):
        """Initialize repository with database session.

        Args:
            session: AsyncSession for database operations
        """
        super().__init__(
            session=session,
            entity_class=ElectionMember,
            model_class=ElectionMemberModel,
        )

    async def get_by_election_id(self, election_id: int) -> list[ElectionMember]:
        """選挙IDに属する全メンバーを取得.

        Args:
            election_id: 選挙ID

        Returns:
            選挙結果メンバーエンティティのリスト
        """
        try:
            query = text("""
                SELECT
                    id,
                    election_id,
                    politician_id,
                    result,
                    votes,
                    rank,
                    created_at,
                    updated_at
                FROM election_members
                WHERE election_id = :election_id
                ORDER BY rank ASC NULLS LAST, id ASC
            """)

            result = await self.session.execute(query, {"election_id": election_id})
            rows = result.fetchall()

            results = []
            for row in rows:
                if hasattr(row, "_asdict"):
                    row_dict = row._asdict()  # type: ignore[attr-defined]
                elif hasattr(row, "_mapping"):
                    row_dict = dict(row._mapping)  # type: ignore[attr-defined]
                else:
                    row_dict = dict(row)
                results.append(self._dict_to_entity(row_dict))
            return results

        except SQLAlchemyError as e:
            logger.error(f"Database error getting election members by election: {e}")
            raise DatabaseError(
                "Failed to get election members by election",
                {"election_id": election_id, "error": str(e)},
            ) from e

    async def get_by_politician_id(self, politician_id: int) -> list[ElectionMember]:
        """政治家IDに紐づく全選挙結果を取得.

        Args:
            politician_id: 政治家ID

        Returns:
            選挙結果メンバーエンティティのリスト
        """
        try:
            query = text("""
                SELECT
                    id,
                    election_id,
                    politician_id,
                    result,
                    votes,
                    rank,
                    created_at,
                    updated_at
                FROM election_members
                WHERE politician_id = :politician_id
                ORDER BY id ASC
            """)

            result = await self.session.execute(query, {"politician_id": politician_id})
            rows = result.fetchall()

            results = []
            for row in rows:
                if hasattr(row, "_asdict"):
                    row_dict = row._asdict()  # type: ignore[attr-defined]
                elif hasattr(row, "_mapping"):
                    row_dict = dict(row._mapping)  # type: ignore[attr-defined]
                else:
                    row_dict = dict(row)
                results.append(self._dict_to_entity(row_dict))
            return results

        except SQLAlchemyError as e:
            logger.error(f"Database error getting election members by politician: {e}")
            raise DatabaseError(
                "Failed to get election members by politician",
                {"politician_id": politician_id, "error": str(e)},
            ) from e

    async def get_all(
        self, limit: int | None = None, offset: int | None = 0
    ) -> list[ElectionMember]:
        """Get all election members.

        Args:
            limit: Maximum number of results
            offset: Number of results to skip

        Returns:
            List of ElectionMember entities
        """
        try:
            query_text = """
                SELECT
                    em.id,
                    em.election_id,
                    em.politician_id,
                    em.result,
                    em.votes,
                    em.rank,
                    em.created_at,
                    em.updated_at
                FROM election_members em
                ORDER BY em.election_id, em.rank ASC NULLS LAST, em.id
            """

            params: dict[str, int | None] = {}
            if limit is not None:
                query_text += " LIMIT :limit OFFSET :offset"
                params = {"limit": limit, "offset": offset or 0}

            result = await self.session.execute(text(query_text), params)
            rows = result.fetchall()

            results = []
            for row in rows:
                if hasattr(row, "_asdict"):
                    row_dict = row._asdict()  # type: ignore[attr-defined]
                elif hasattr(row, "_mapping"):
                    row_dict = dict(row._mapping)  # type: ignore[attr-defined]
                else:
                    row_dict = dict(row)
                results.append(self._dict_to_entity(row_dict))
            return results

        except SQLAlchemyError as e:
            logger.error(f"Database error getting all election members: {e}")
            raise DatabaseError(
                "Failed to get all election members", {"error": str(e)}
            ) from e

    async def get_by_id(self, entity_id: int) -> ElectionMember | None:
        """Get election member by ID.

        Args:
            entity_id: ElectionMember ID

        Returns:
            ElectionMember entity or None if not found
        """
        try:
            query = text("""
                SELECT
                    id,
                    election_id,
                    politician_id,
                    result,
                    votes,
                    rank,
                    created_at,
                    updated_at
                FROM election_members
                WHERE id = :id
            """)

            result = await self.session.execute(query, {"id": entity_id})
            row = result.first()

            if row:
                if hasattr(row, "_asdict"):
                    row_dict = row._asdict()  # type: ignore[attr-defined]
                elif hasattr(row, "_mapping"):
                    row_dict = dict(row._mapping)  # type: ignore[attr-defined]
                else:
                    row_dict = dict(row)
                return self._dict_to_entity(row_dict)
            return None

        except SQLAlchemyError as e:
            logger.error(f"Database error getting election member by ID: {e}")
            raise DatabaseError(
                "Failed to get election member by ID",
                {"id": entity_id, "error": str(e)},
            ) from e

    async def create(self, entity: ElectionMember) -> ElectionMember:
        """Create a new election member.

        Args:
            entity: ElectionMember entity to create

        Returns:
            Created ElectionMember entity with ID
        """
        try:
            query = text("""
                INSERT INTO election_members (
                    election_id, politician_id,
                    result, votes, rank,
                    created_at, updated_at
                )
                VALUES (
                    :election_id, :politician_id,
                    :result, :votes, :rank,
                    :created_at, :updated_at
                )
                RETURNING *
            """)

            params = {
                "election_id": entity.election_id,
                "politician_id": entity.politician_id,
                "result": entity.result,
                "votes": entity.votes,
                "rank": entity.rank,
                "created_at": datetime.now(),
                "updated_at": datetime.now(),
            }

            result = await self.session.execute(query, params)
            await self.session.commit()

            row = result.first()
            if row:
                if hasattr(row, "_asdict"):
                    row_dict = row._asdict()  # type: ignore[attr-defined]
                elif hasattr(row, "_mapping"):
                    row_dict = dict(row._mapping)  # type: ignore[attr-defined]
                else:
                    row_dict = dict(row)
                return self._dict_to_entity(row_dict)
            raise RuntimeError("Failed to create election member")

        except SQLAlchemyError as e:
            logger.error(f"Database error creating election member: {e}")
            await self.session.rollback()
            raise DatabaseError(
                "Failed to create election member",
                {"entity": str(entity), "error": str(e)},
            ) from e

    async def update(self, entity: ElectionMember) -> ElectionMember:
        """Update an existing election member.

        Args:
            entity: ElectionMember entity to update

        Returns:
            Updated ElectionMember entity
        """
        try:
            query = text("""
                UPDATE election_members
                SET election_id = :election_id,
                    politician_id = :politician_id,
                    result = :result,
                    votes = :votes,
                    rank = :rank,
                    updated_at = :updated_at
                WHERE id = :id
                RETURNING *
            """)

            params = {
                "id": entity.id,
                "election_id": entity.election_id,
                "politician_id": entity.politician_id,
                "result": entity.result,
                "votes": entity.votes,
                "rank": entity.rank,
                "updated_at": datetime.now(),
            }

            result = await self.session.execute(query, params)
            await self.session.commit()

            row = result.first()
            if row:
                if hasattr(row, "_asdict"):
                    row_dict = row._asdict()  # type: ignore[attr-defined]
                elif hasattr(row, "_mapping"):
                    row_dict = dict(row._mapping)  # type: ignore[attr-defined]
                else:
                    row_dict = dict(row)
                return self._dict_to_entity(row_dict)
            raise UpdateError(f"ElectionMember with ID {entity.id} not found")

        except SQLAlchemyError as e:
            logger.error(f"Database error updating election member: {e}")
            await self.session.rollback()
            raise DatabaseError(
                "Failed to update election member",
                {"entity": str(entity), "error": str(e)},
            ) from e

    async def delete(self, entity_id: int) -> bool:
        """Delete an election member by ID.

        Args:
            entity_id: ElectionMember ID to delete

        Returns:
            True if deleted, False otherwise
        """
        try:
            query = text("DELETE FROM election_members WHERE id = :id")
            result = await self.session.execute(query, {"id": entity_id})
            await self.session.commit()

            return result.rowcount > 0  # type: ignore[attr-defined]

        except SQLAlchemyError as e:
            logger.error(f"Database error deleting election member: {e}")
            await self.session.rollback()
            raise DatabaseError(
                "Failed to delete election member",
                {"id": entity_id, "error": str(e)},
            ) from e

    async def count(self) -> int:
        """Count total number of election members."""
        query = text("SELECT COUNT(*) FROM election_members")
        result = await self.session.execute(query)
        count = result.scalar()
        return count if count is not None else 0

    def _to_entity(self, model: ElectionMemberModel) -> ElectionMember:
        """Convert database model to domain entity.

        Args:
            model: Database model

        Returns:
            Domain entity
        """
        return ElectionMember(
            id=model.id,
            election_id=model.election_id,
            politician_id=model.politician_id,
            result=model.result,
            votes=model.votes,
            rank=model.rank,
        )

    def _to_model(self, entity: ElectionMember) -> ElectionMemberModel:
        """Convert domain entity to database model.

        Args:
            entity: Domain entity

        Returns:
            Database model
        """
        return ElectionMemberModel(
            id=entity.id,
            election_id=entity.election_id,
            politician_id=entity.politician_id,
            result=entity.result,
            votes=entity.votes,
            rank=entity.rank,
        )

    def _update_model(self, model: ElectionMemberModel, entity: ElectionMember) -> None:
        """Update model from entity.

        Args:
            model: Database model to update
            entity: Source entity
        """
        model.election_id = entity.election_id
        model.politician_id = entity.politician_id
        model.result = entity.result
        model.votes = entity.votes
        model.rank = entity.rank

    def _dict_to_entity(self, data: dict[str, Any]) -> ElectionMember:
        """Convert dictionary to entity.

        Args:
            data: Dictionary with entity data

        Returns:
            ElectionMember entity
        """
        return ElectionMember(
            id=data.get("id"),
            election_id=data["election_id"],
            politician_id=data["politician_id"],
            result=data["result"],
            votes=data.get("votes"),
            rank=data.get("rank"),
        )
