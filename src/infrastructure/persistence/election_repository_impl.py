"""Election repository implementation using SQLAlchemy."""

import logging

from datetime import date, datetime
from typing import Any

from pydantic import BaseModel as PydanticBaseModel
from sqlalchemy import text
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.ext.asyncio import AsyncSession

from src.domain.entities.election import Election
from src.domain.repositories.election_repository import ElectionRepository
from src.domain.repositories.session_adapter import ISessionAdapter
from src.infrastructure.exceptions import (
    DatabaseError,
    UpdateError,
)
from src.infrastructure.persistence.base_repository_impl import BaseRepositoryImpl


logger = logging.getLogger(__name__)


class ElectionModel(PydanticBaseModel):
    """Election database model."""

    id: int | None = None
    governing_body_id: int
    term_number: int
    election_date: date
    election_type: str | None = None
    created_at: datetime | None = None
    updated_at: datetime | None = None

    class Config:
        arbitrary_types_allowed = True


class ElectionRepositoryImpl(BaseRepositoryImpl[Election], ElectionRepository):
    """Election repository implementation using SQLAlchemy."""

    def __init__(self, session: AsyncSession | ISessionAdapter):
        """Initialize repository with database session.

        Args:
            session: AsyncSession for database operations
        """
        super().__init__(
            session=session,
            entity_class=Election,
            model_class=ElectionModel,
        )

    async def get_by_governing_body(self, governing_body_id: int) -> list[Election]:
        """開催主体に属する全選挙を取得.

        Args:
            governing_body_id: 開催主体ID

        Returns:
            選挙エンティティのリスト（選挙日の降順）
        """
        try:
            query = text("""
                SELECT
                    id,
                    governing_body_id,
                    term_number,
                    election_date,
                    election_type,
                    created_at,
                    updated_at
                FROM elections
                WHERE governing_body_id = :governing_body_id
                ORDER BY election_date DESC
            """)

            result = await self.session.execute(
                query, {"governing_body_id": governing_body_id}
            )
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
            logger.error(f"Database error getting elections by governing body: {e}")
            raise DatabaseError(
                "Failed to get elections by governing body",
                {"governing_body_id": governing_body_id, "error": str(e)},
            ) from e

    async def get_by_governing_body_and_term(
        self, governing_body_id: int, term_number: int
    ) -> Election | None:
        """開催主体と期番号で選挙を取得.

        Args:
            governing_body_id: 開催主体ID
            term_number: 期番号

        Returns:
            選挙エンティティ、見つからない場合はNone
        """
        try:
            query = text("""
                SELECT
                    id,
                    governing_body_id,
                    term_number,
                    election_date,
                    election_type,
                    created_at,
                    updated_at
                FROM elections
                WHERE governing_body_id = :governing_body_id
                AND term_number = :term_number
            """)

            result = await self.session.execute(
                query,
                {"governing_body_id": governing_body_id, "term_number": term_number},
            )
            row = result.fetchone()

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
            logger.error(f"Database error getting election: {e}")
            raise DatabaseError(
                "Failed to get election by governing body and term",
                {
                    "governing_body_id": governing_body_id,
                    "term_number": term_number,
                    "error": str(e),
                },
            ) from e

    async def get_all(
        self, limit: int | None = None, offset: int | None = 0
    ) -> list[Election]:
        """Get all elections.

        Args:
            limit: Maximum number of results
            offset: Number of results to skip

        Returns:
            List of Election entities
        """
        try:
            query_text = """
                SELECT
                    e.id,
                    e.governing_body_id,
                    e.term_number,
                    e.election_date,
                    e.election_type,
                    e.created_at,
                    e.updated_at
                FROM elections e
                ORDER BY e.election_date DESC, e.governing_body_id
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
            logger.error(f"Database error getting all elections: {e}")
            raise DatabaseError("Failed to get all elections", {"error": str(e)}) from e

    async def get_by_id(self, entity_id: int) -> Election | None:
        """Get election by ID.

        Args:
            entity_id: Election ID

        Returns:
            Election entity or None if not found
        """
        try:
            query = text("""
                SELECT
                    id,
                    governing_body_id,
                    term_number,
                    election_date,
                    election_type,
                    created_at,
                    updated_at
                FROM elections
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
            logger.error(f"Database error getting election by ID: {e}")
            raise DatabaseError(
                "Failed to get election by ID", {"id": entity_id, "error": str(e)}
            ) from e

    async def create(self, entity: Election) -> Election:
        """Create a new election.

        Args:
            entity: Election entity to create

        Returns:
            Created Election entity with ID
        """
        try:
            query = text("""
                INSERT INTO elections (
                    governing_body_id, term_number,
                    election_date, election_type,
                    created_at, updated_at
                )
                VALUES (
                    :governing_body_id, :term_number,
                    :election_date, :election_type,
                    :created_at, :updated_at
                )
                RETURNING *
            """)

            params = {
                "governing_body_id": entity.governing_body_id,
                "term_number": entity.term_number,
                "election_date": entity.election_date,
                "election_type": entity.election_type,
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
            raise RuntimeError("Failed to create election")

        except SQLAlchemyError as e:
            logger.error(f"Database error creating election: {e}")
            await self.session.rollback()
            raise DatabaseError(
                "Failed to create election", {"entity": str(entity), "error": str(e)}
            ) from e

    async def update(self, entity: Election) -> Election:
        """Update an existing election.

        Args:
            entity: Election entity to update

        Returns:
            Updated Election entity
        """
        try:
            query = text("""
                UPDATE elections
                SET governing_body_id = :governing_body_id,
                    term_number = :term_number,
                    election_date = :election_date,
                    election_type = :election_type,
                    updated_at = :updated_at
                WHERE id = :id
                RETURNING *
            """)

            params = {
                "id": entity.id,
                "governing_body_id": entity.governing_body_id,
                "term_number": entity.term_number,
                "election_date": entity.election_date,
                "election_type": entity.election_type,
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
            raise UpdateError(f"Election with ID {entity.id} not found")

        except SQLAlchemyError as e:
            logger.error(f"Database error updating election: {e}")
            await self.session.rollback()
            raise DatabaseError(
                "Failed to update election", {"entity": str(entity), "error": str(e)}
            ) from e

    async def delete(self, entity_id: int) -> bool:
        """Delete an election by ID.

        Args:
            entity_id: Election ID to delete

        Returns:
            True if deleted, False otherwise
        """
        try:
            # Check if there are related conferences
            check_conferences_query = text("""
                SELECT COUNT(*) FROM conferences WHERE election_id = :election_id
            """)
            result = await self.session.execute(
                check_conferences_query, {"election_id": entity_id}
            )
            conferences_count = result.scalar()

            if conferences_count and conferences_count > 0:
                return False  # Cannot delete if there are related conferences

            # Delete the election
            query = text("DELETE FROM elections WHERE id = :id")
            result = await self.session.execute(query, {"id": entity_id})
            await self.session.commit()

            return result.rowcount > 0  # type: ignore[attr-defined]

        except SQLAlchemyError as e:
            logger.error(f"Database error deleting election: {e}")
            await self.session.rollback()
            raise DatabaseError(
                "Failed to delete election", {"id": entity_id, "error": str(e)}
            ) from e

    async def count(self) -> int:
        """Count total number of elections."""
        query = text("SELECT COUNT(*) FROM elections")
        result = await self.session.execute(query)
        count = result.scalar()
        return count if count is not None else 0

    def _to_entity(self, model: ElectionModel) -> Election:
        """Convert database model to domain entity.

        Args:
            model: Database model

        Returns:
            Domain entity
        """
        return Election(
            id=model.id,
            governing_body_id=model.governing_body_id,
            term_number=model.term_number,
            election_date=model.election_date,
            election_type=model.election_type,
        )

    def _to_model(self, entity: Election) -> ElectionModel:
        """Convert domain entity to database model.

        Args:
            entity: Domain entity

        Returns:
            Database model
        """
        return ElectionModel(
            id=entity.id,
            governing_body_id=entity.governing_body_id,
            term_number=entity.term_number,
            election_date=entity.election_date,
            election_type=entity.election_type,
        )

    def _update_model(self, model: ElectionModel, entity: Election) -> None:
        """Update model from entity.

        Args:
            model: Database model to update
            entity: Source entity
        """
        model.governing_body_id = entity.governing_body_id
        model.term_number = entity.term_number
        model.election_date = entity.election_date
        model.election_type = entity.election_type

    def _dict_to_entity(self, data: dict[str, Any]) -> Election:
        """Convert dictionary to entity.

        Args:
            data: Dictionary with entity data

        Returns:
            Election entity
        """
        return Election(
            id=data.get("id"),
            governing_body_id=data["governing_body_id"],
            term_number=data["term_number"],
            election_date=data["election_date"],
            election_type=data.get("election_type"),
        )
