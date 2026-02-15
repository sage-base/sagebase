"""ProposalJudge repository implementation using SQLAlchemy."""

import logging

from datetime import datetime
from typing import Any

from pydantic import BaseModel as PydanticBaseModel
from sqlalchemy import text
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.ext.asyncio import AsyncSession

from src.domain.entities.proposal_judge import ProposalJudge
from src.domain.repositories.proposal_judge_repository import ProposalJudgeRepository
from src.domain.repositories.session_adapter import ISessionAdapter
from src.infrastructure.exceptions import DatabaseError
from src.infrastructure.persistence.base_repository_impl import BaseRepositoryImpl


logger = logging.getLogger(__name__)

_SELECT_COLUMNS = """
    id, proposal_id, politician_id, approve,
    source_type, source_group_judge_id, is_defection,
    created_at, updated_at
"""

_RETURNING_COLUMNS = f"RETURNING {_SELECT_COLUMNS}"


class ProposalJudgeModel(PydanticBaseModel):
    """ProposalJudge database model."""

    id: int | None = None
    proposal_id: int
    politician_id: int
    approve: str | None = None
    source_type: str | None = None
    source_group_judge_id: int | None = None
    is_defection: bool | None = None
    created_at: datetime | None = None
    updated_at: datetime | None = None

    class Config:
        arbitrary_types_allowed = True


class ProposalJudgeRepositoryImpl(
    BaseRepositoryImpl[ProposalJudge], ProposalJudgeRepository
):
    """ProposalJudge repository implementation using SQLAlchemy."""

    def __init__(self, session: AsyncSession | ISessionAdapter):
        """Initialize repository with database session.

        Args:
            session: AsyncSession for database operations
        """
        super().__init__(
            session=session,
            entity_class=ProposalJudge,
            model_class=ProposalJudgeModel,
        )

    def _row_to_dict(self, row: Any) -> dict[str, Any]:
        """Convert a database row to a dictionary."""
        if hasattr(row, "_asdict"):
            return row._asdict()  # type: ignore[attr-defined]
        elif hasattr(row, "_mapping"):
            return dict(row._mapping)  # type: ignore[attr-defined]
        return dict(row)

    def _rows_to_entities(self, rows: Any) -> list[ProposalJudge]:
        """Convert multiple database rows to entities."""
        return [self._dict_to_entity(self._row_to_dict(row)) for row in rows]

    async def get_by_proposal(self, proposal_id: int) -> list[ProposalJudge]:
        """Get all judges for a proposal.

        Args:
            proposal_id: ID of the proposal

        Returns:
            List of proposal judges for the specified proposal
        """
        try:
            query = text(f"""
                SELECT {_SELECT_COLUMNS}
                FROM proposal_judges
                WHERE proposal_id = :proposal_id
                ORDER BY created_at DESC
            """)

            result = await self.session.execute(query, {"proposal_id": proposal_id})
            return self._rows_to_entities(result.fetchall())

        except SQLAlchemyError as e:
            logger.error(f"Database error getting judges by proposal: {e}")
            raise DatabaseError(
                "Failed to get judges by proposal",
                {"proposal_id": proposal_id, "error": str(e)},
            ) from e

    async def get_by_politician(self, politician_id: int) -> list[ProposalJudge]:
        """Get all proposal judges by a politician.

        Args:
            politician_id: ID of the politician

        Returns:
            List of proposal judges by the specified politician
        """
        try:
            query = text(f"""
                SELECT {_SELECT_COLUMNS}
                FROM proposal_judges
                WHERE politician_id = :politician_id
                ORDER BY created_at DESC
            """)

            result = await self.session.execute(query, {"politician_id": politician_id})
            return self._rows_to_entities(result.fetchall())

        except SQLAlchemyError as e:
            logger.error(f"Database error getting judges by politician: {e}")
            raise DatabaseError(
                "Failed to get judges by politician",
                {"politician_id": politician_id, "error": str(e)},
            ) from e

    async def get_by_proposal_and_politician(
        self, proposal_id: int, politician_id: int
    ) -> ProposalJudge | None:
        """Get a specific judge by proposal and politician.

        Args:
            proposal_id: ID of the proposal
            politician_id: ID of the politician

        Returns:
            The proposal judge if found, None otherwise
        """
        try:
            query = text(f"""
                SELECT {_SELECT_COLUMNS}
                FROM proposal_judges
                WHERE proposal_id = :proposal_id
                AND politician_id = :politician_id
            """)

            result = await self.session.execute(
                query, {"proposal_id": proposal_id, "politician_id": politician_id}
            )
            row = result.fetchone()

            if row:
                return self._dict_to_entity(self._row_to_dict(row))
            return None

        except SQLAlchemyError as e:
            logger.error(
                f"Database error getting judge by proposal and politician: {e}"
            )
            raise DatabaseError(
                "Failed to get judge by proposal and politician",
                {
                    "proposal_id": proposal_id,
                    "politician_id": politician_id,
                    "error": str(e),
                },
            ) from e

    async def bulk_create(self, judges: list[ProposalJudge]) -> list[ProposalJudge]:
        """Create multiple proposal judges at once.

        Args:
            judges: List of ProposalJudge entities to create

        Returns:
            List of created ProposalJudge entities with IDs
        """
        if not judges:
            return []

        try:
            values = []
            for judge in judges:
                values.append(
                    {
                        "proposal_id": judge.proposal_id,
                        "politician_id": judge.politician_id,
                        "approve": judge.approve,
                        "source_type": judge.source_type,
                        "source_group_judge_id": judge.source_group_judge_id,
                        "is_defection": judge.is_defection,
                    }
                )

            query = text(f"""
                INSERT INTO proposal_judges (
                    proposal_id, politician_id, approve,
                    source_type, source_group_judge_id, is_defection
                )
                VALUES (
                    :proposal_id, :politician_id, :approve,
                    :source_type, :source_group_judge_id, :is_defection
                )
                {_RETURNING_COLUMNS}
            """)

            created_judges = []
            for value in values:
                result = await self.session.execute(query, value)
                row = result.fetchone()
                if row:
                    created_judges.append(self._dict_to_entity(self._row_to_dict(row)))

            await self.session.commit()
            return created_judges

        except SQLAlchemyError as e:
            logger.error(f"Database error bulk creating proposal judges: {e}")
            await self.session.rollback()
            raise DatabaseError(
                "Failed to bulk create proposal judges",
                {"count": len(judges), "error": str(e)},
            ) from e

    async def get_by_source_group_judge_id(
        self, source_group_judge_id: int
    ) -> list[ProposalJudge]:
        """Get all judges created from a specific group judge.

        Args:
            source_group_judge_id: ID of the source ProposalParliamentaryGroupJudge

        Returns:
            List of proposal judges created from the specified group judge
        """
        try:
            query = text(f"""
                SELECT {_SELECT_COLUMNS}
                FROM proposal_judges
                WHERE source_group_judge_id = :source_group_judge_id
                ORDER BY created_at DESC
            """)

            result = await self.session.execute(
                query, {"source_group_judge_id": source_group_judge_id}
            )
            return self._rows_to_entities(result.fetchall())

        except SQLAlchemyError as e:
            logger.error(f"Database error getting judges by source group judge ID: {e}")
            raise DatabaseError(
                "Failed to get judges by source group judge ID",
                {"source_group_judge_id": source_group_judge_id, "error": str(e)},
            ) from e

    async def get_all(
        self, limit: int | None = None, offset: int | None = None
    ) -> list[ProposalJudge]:
        """Get all proposal judges.

        Args:
            limit: Maximum number of results
            offset: Number of results to skip

        Returns:
            List of ProposalJudge entities
        """
        try:
            query_text = f"""
                SELECT {_SELECT_COLUMNS}
                FROM proposal_judges
                ORDER BY created_at DESC
            """

            params: dict[str, int | None] = {}
            if limit is not None:
                query_text += " LIMIT :limit OFFSET :offset"
                params = {"limit": limit, "offset": offset or 0}

            result = await self.session.execute(text(query_text), params)
            return self._rows_to_entities(result.fetchall())

        except SQLAlchemyError as e:
            logger.error(f"Database error getting all proposal judges: {e}")
            raise DatabaseError(
                "Failed to get all proposal judges", {"error": str(e)}
            ) from e

    async def get_by_id(self, entity_id: int) -> ProposalJudge | None:
        """Get proposal judge by ID.

        Args:
            entity_id: ProposalJudge ID

        Returns:
            ProposalJudge entity or None if not found
        """
        try:
            query = text(f"""
                SELECT {_SELECT_COLUMNS}
                FROM proposal_judges
                WHERE id = :id
            """)

            result = await self.session.execute(query, {"id": entity_id})
            row = result.fetchone()

            if row:
                return self._dict_to_entity(self._row_to_dict(row))
            return None

        except SQLAlchemyError as e:
            logger.error(f"Database error getting proposal judge by ID: {e}")
            raise DatabaseError(
                "Failed to get proposal judge by ID",
                {"id": entity_id, "error": str(e)},
            ) from e

    async def get_by_ids(self, entity_ids: list[int]) -> list[ProposalJudge]:
        """Get multiple proposal judges by IDs.

        Args:
            entity_ids: List of ProposalJudge IDs

        Returns:
            List of ProposalJudge entities
        """
        if not entity_ids:
            return []

        try:
            placeholders = ", ".join(f":id_{i}" for i in range(len(entity_ids)))
            query = text(f"""
                SELECT {_SELECT_COLUMNS}
                FROM proposal_judges
                WHERE id IN ({placeholders})
            """)
            params = {f"id_{i}": eid for i, eid in enumerate(entity_ids)}

            result = await self.session.execute(query, params)
            return self._rows_to_entities(result.fetchall())

        except SQLAlchemyError as e:
            logger.error(f"Database error getting proposal judges by IDs: {e}")
            raise DatabaseError(
                "Failed to get proposal judges by IDs",
                {"entity_ids": entity_ids, "error": str(e)},
            ) from e

    async def count(self) -> int:
        """Count total number of proposal judges."""
        try:
            query = text("SELECT COUNT(*) FROM proposal_judges")
            result = await self.session.execute(query)
            count = result.scalar()
            return count if count is not None else 0

        except SQLAlchemyError as e:
            logger.error(f"Database error counting proposal judges: {e}")
            raise DatabaseError(
                "Failed to count proposal judges", {"error": str(e)}
            ) from e

    async def create(self, entity: ProposalJudge) -> ProposalJudge:
        """Create a new proposal judge.

        Args:
            entity: ProposalJudge entity to create

        Returns:
            Created ProposalJudge entity with ID
        """
        try:
            query = text(f"""
                INSERT INTO proposal_judges (
                    proposal_id, politician_id, approve,
                    source_type, source_group_judge_id, is_defection
                )
                VALUES (
                    :proposal_id, :politician_id, :approve,
                    :source_type, :source_group_judge_id, :is_defection
                )
                {_RETURNING_COLUMNS}
            """)

            result = await self.session.execute(
                query,
                {
                    "proposal_id": entity.proposal_id,
                    "politician_id": entity.politician_id,
                    "approve": entity.approve,
                    "source_type": entity.source_type,
                    "source_group_judge_id": entity.source_group_judge_id,
                    "is_defection": entity.is_defection,
                },
            )
            row = result.fetchone()
            await self.session.commit()

            if row:
                return self._dict_to_entity(self._row_to_dict(row))

            raise DatabaseError("Failed to create proposal judge", {"entity": entity})

        except SQLAlchemyError as e:
            logger.error(f"Database error creating proposal judge: {e}")
            await self.session.rollback()
            raise DatabaseError(
                "Failed to create proposal judge", {"entity": entity, "error": str(e)}
            ) from e

    async def update(self, entity: ProposalJudge) -> ProposalJudge:
        """Update an existing proposal judge.

        Args:
            entity: ProposalJudge entity with updated values

        Returns:
            Updated ProposalJudge entity
        """
        if not entity.id:
            raise ValueError("Entity must have an ID to update")

        try:
            query = text(f"""
                UPDATE proposal_judges
                SET proposal_id = :proposal_id,
                    politician_id = :politician_id,
                    approve = :approve,
                    source_type = :source_type,
                    source_group_judge_id = :source_group_judge_id,
                    is_defection = :is_defection,
                    updated_at = CURRENT_TIMESTAMP
                WHERE id = :id
                {_RETURNING_COLUMNS}
            """)

            result = await self.session.execute(
                query,
                {
                    "id": entity.id,
                    "proposal_id": entity.proposal_id,
                    "politician_id": entity.politician_id,
                    "approve": entity.approve,
                    "source_type": entity.source_type,
                    "source_group_judge_id": entity.source_group_judge_id,
                    "is_defection": entity.is_defection,
                },
            )
            row = result.fetchone()
            await self.session.commit()

            if row:
                return self._dict_to_entity(self._row_to_dict(row))

            raise DatabaseError(
                f"ProposalJudge with ID {entity.id} not found", {"entity": entity}
            )

        except SQLAlchemyError as e:
            logger.error(f"Database error updating proposal judge: {e}")
            await self.session.rollback()
            raise DatabaseError(
                "Failed to update proposal judge", {"entity": entity, "error": str(e)}
            ) from e

    async def delete(self, entity_id: int) -> bool:
        """Delete a proposal judge by ID.

        Args:
            entity_id: ProposalJudge ID to delete

        Returns:
            True if deleted, False otherwise
        """
        try:
            query = text("DELETE FROM proposal_judges WHERE id = :id")
            result = await self.session.execute(query, {"id": entity_id})
            await self.session.commit()

            return result.rowcount > 0  # type: ignore[attr-defined]

        except SQLAlchemyError as e:
            logger.error(f"Database error deleting proposal judge: {e}")
            await self.session.rollback()
            raise DatabaseError(
                "Failed to delete proposal judge", {"id": entity_id, "error": str(e)}
            ) from e

    async def bulk_update(self, judges: list[ProposalJudge]) -> list[ProposalJudge]:
        """Update multiple proposal judges at once.

        Args:
            judges: List of ProposalJudge entities to update

        Returns:
            List of updated ProposalJudge entities
        """
        if not judges:
            return []

        try:
            query = text(f"""
                UPDATE proposal_judges
                SET proposal_id = :proposal_id,
                    politician_id = :politician_id,
                    approve = :approve,
                    source_type = :source_type,
                    source_group_judge_id = :source_group_judge_id,
                    is_defection = :is_defection,
                    updated_at = CURRENT_TIMESTAMP
                WHERE id = :id
                {_RETURNING_COLUMNS}
            """)

            updated: list[ProposalJudge] = []
            for judge in judges:
                if not judge.id:
                    raise ValueError("Entity must have an ID to update")
                result = await self.session.execute(
                    query,
                    {
                        "id": judge.id,
                        "proposal_id": judge.proposal_id,
                        "politician_id": judge.politician_id,
                        "approve": judge.approve,
                        "source_type": judge.source_type,
                        "source_group_judge_id": judge.source_group_judge_id,
                        "is_defection": judge.is_defection,
                    },
                )
                row = result.fetchone()
                if row:
                    updated.append(self._dict_to_entity(self._row_to_dict(row)))

            await self.session.commit()
            return updated

        except SQLAlchemyError as e:
            logger.error(f"Database error bulk updating proposal judges: {e}")
            await self.session.rollback()
            raise DatabaseError(
                "Failed to bulk update proposal judges",
                {"count": len(judges), "error": str(e)},
            ) from e

    def _to_entity(self, model: ProposalJudgeModel) -> ProposalJudge:
        """Convert database model to domain entity.

        Args:
            model: Database model

        Returns:
            Domain entity
        """
        entity = ProposalJudge(
            id=model.id,
            proposal_id=model.proposal_id,
            politician_id=model.politician_id,
            approve=model.approve,
            source_type=model.source_type,
            source_group_judge_id=model.source_group_judge_id,
            is_defection=model.is_defection,
        )
        entity.created_at = model.created_at
        entity.updated_at = model.updated_at
        return entity

    def _to_model(self, entity: ProposalJudge) -> ProposalJudgeModel:
        """Convert domain entity to database model.

        Args:
            entity: Domain entity

        Returns:
            Database model
        """
        return ProposalJudgeModel(
            id=entity.id,
            proposal_id=entity.proposal_id,
            politician_id=entity.politician_id,
            approve=entity.approve,
            source_type=entity.source_type,
            source_group_judge_id=entity.source_group_judge_id,
            is_defection=entity.is_defection,
        )

    def _update_model(self, model: ProposalJudgeModel, entity: ProposalJudge) -> None:
        """Update model from entity.

        Args:
            model: Database model to update
            entity: Source entity
        """
        model.proposal_id = entity.proposal_id
        model.politician_id = entity.politician_id
        model.approve = entity.approve
        model.source_type = entity.source_type
        model.source_group_judge_id = entity.source_group_judge_id
        model.is_defection = entity.is_defection

    def _dict_to_entity(self, data: dict[str, Any]) -> ProposalJudge:
        """Convert dictionary to entity.

        Args:
            data: Dictionary with entity data

        Returns:
            ProposalJudge entity
        """
        entity = ProposalJudge(
            id=data.get("id"),
            proposal_id=data["proposal_id"],
            politician_id=data["politician_id"],
            approve=data.get("approve"),
            source_type=data.get("source_type"),
            source_group_judge_id=data.get("source_group_judge_id"),
            is_defection=data.get("is_defection"),
        )
        entity.created_at = data.get("created_at")
        entity.updated_at = data.get("updated_at")
        return entity
