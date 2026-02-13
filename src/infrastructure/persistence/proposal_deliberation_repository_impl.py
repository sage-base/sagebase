"""ProposalDeliberation repository implementation using SQLAlchemy."""

import logging

from datetime import datetime
from typing import Any

from pydantic import BaseModel as PydanticBaseModel
from sqlalchemy import text
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.ext.asyncio import AsyncSession

from src.domain.entities.proposal_deliberation import ProposalDeliberation
from src.domain.repositories.proposal_deliberation_repository import (
    ProposalDeliberationRepository,
)
from src.domain.repositories.session_adapter import ISessionAdapter
from src.infrastructure.exceptions import DatabaseError
from src.infrastructure.persistence.base_repository_impl import BaseRepositoryImpl


logger = logging.getLogger(__name__)


class ProposalDeliberationModel(PydanticBaseModel):
    """ProposalDeliberation database model."""

    id: int | None = None
    proposal_id: int
    conference_id: int
    meeting_id: int | None = None
    stage: str | None = None
    created_at: datetime | None = None
    updated_at: datetime | None = None

    class Config:
        arbitrary_types_allowed = True


_SELECT_COLUMNS = """
    id,
    proposal_id,
    conference_id,
    meeting_id,
    stage,
    created_at,
    updated_at
"""


class ProposalDeliberationRepositoryImpl(
    BaseRepositoryImpl[ProposalDeliberation], ProposalDeliberationRepository
):
    """ProposalDeliberation repository implementation using SQLAlchemy."""

    def __init__(self, session: AsyncSession | ISessionAdapter):
        super().__init__(
            session=session,
            entity_class=ProposalDeliberation,
            model_class=ProposalDeliberationModel,
        )

    def _row_to_dict(self, row: Any) -> dict[str, Any]:
        if hasattr(row, "_asdict"):
            return row._asdict()
        elif hasattr(row, "_mapping"):
            return dict(row._mapping)
        return dict(row)

    def _dict_to_entity(self, data: dict[str, Any]) -> ProposalDeliberation:
        entity = ProposalDeliberation(
            id=data.get("id"),
            proposal_id=data["proposal_id"],
            conference_id=data["conference_id"],
            meeting_id=data.get("meeting_id"),
            stage=data.get("stage"),
        )
        entity.created_at = data.get("created_at")
        entity.updated_at = data.get("updated_at")
        return entity

    def _to_entity(self, model: ProposalDeliberationModel) -> ProposalDeliberation:
        return ProposalDeliberation(
            id=model.id,
            proposal_id=model.proposal_id,
            conference_id=model.conference_id,
            meeting_id=model.meeting_id,
            stage=model.stage,
        )

    def _to_model(self, entity: ProposalDeliberation) -> ProposalDeliberationModel:
        return ProposalDeliberationModel(
            id=entity.id,
            proposal_id=entity.proposal_id,
            conference_id=entity.conference_id,
            meeting_id=entity.meeting_id,
            stage=entity.stage,
        )

    def _update_model(
        self, model: ProposalDeliberationModel, entity: ProposalDeliberation
    ) -> None:
        model.proposal_id = entity.proposal_id
        model.conference_id = entity.conference_id
        model.meeting_id = entity.meeting_id
        model.stage = entity.stage

    async def get_all(
        self, limit: int | None = None, offset: int | None = 0
    ) -> list[ProposalDeliberation]:
        try:
            query_text = f"""
                SELECT {_SELECT_COLUMNS}
                FROM proposal_deliberations
                ORDER BY created_at DESC
            """

            params: dict[str, int | None] = {}
            if limit is not None:
                query_text += " LIMIT :limit OFFSET :offset"
                params = {"limit": limit, "offset": offset or 0}

            result = await self.session.execute(text(query_text), params)
            rows = result.fetchall()

            return [self._dict_to_entity(self._row_to_dict(row)) for row in rows]

        except SQLAlchemyError as e:
            logger.error(f"Database error getting all proposal_deliberations: {e}")
            raise DatabaseError(
                "Failed to get all proposal_deliberations", {"error": str(e)}
            ) from e

    async def get_by_id(self, entity_id: int) -> ProposalDeliberation | None:
        try:
            query = text(f"""
                SELECT {_SELECT_COLUMNS}
                FROM proposal_deliberations
                WHERE id = :id
            """)

            result = await self.session.execute(query, {"id": entity_id})
            row = result.fetchone()

            if row:
                return self._dict_to_entity(self._row_to_dict(row))
            return None

        except SQLAlchemyError as e:
            logger.error(f"Database error getting proposal_deliberation by ID: {e}")
            raise DatabaseError(
                "Failed to get proposal_deliberation by ID",
                {"id": entity_id, "error": str(e)},
            ) from e

    async def get_by_ids(self, entity_ids: list[int]) -> list[ProposalDeliberation]:
        if not entity_ids:
            return []
        try:
            placeholders = ", ".join(f":id_{i}" for i in range(len(entity_ids)))
            query = text(f"""
                SELECT {_SELECT_COLUMNS}
                FROM proposal_deliberations
                WHERE id IN ({placeholders})
                ORDER BY id
            """)
            params = {f"id_{i}": eid for i, eid in enumerate(entity_ids)}

            result = await self.session.execute(query, params)
            rows = result.fetchall()

            return [self._dict_to_entity(self._row_to_dict(row)) for row in rows]

        except SQLAlchemyError as e:
            logger.error(f"Database error getting proposal_deliberations by IDs: {e}")
            raise DatabaseError(
                "Failed to get proposal_deliberations by IDs",
                {"ids": entity_ids, "error": str(e)},
            ) from e

    async def create(self, entity: ProposalDeliberation) -> ProposalDeliberation:
        try:
            query = text(f"""
                INSERT INTO proposal_deliberations (
                    proposal_id, conference_id, meeting_id, stage
                )
                VALUES (
                    :proposal_id, :conference_id, :meeting_id, :stage
                )
                RETURNING {_SELECT_COLUMNS}
            """)

            result = await self.session.execute(
                query,
                {
                    "proposal_id": entity.proposal_id,
                    "conference_id": entity.conference_id,
                    "meeting_id": entity.meeting_id,
                    "stage": entity.stage,
                },
            )
            row = result.fetchone()
            await self.session.commit()

            if row:
                return self._dict_to_entity(self._row_to_dict(row))

            raise DatabaseError(
                "Failed to create proposal_deliberation", {"entity": entity}
            )

        except SQLAlchemyError as e:
            logger.error(f"Database error creating proposal_deliberation: {e}")
            await self.session.rollback()
            raise DatabaseError(
                "Failed to create proposal_deliberation",
                {"entity": entity, "error": str(e)},
            ) from e

    async def update(self, entity: ProposalDeliberation) -> ProposalDeliberation:
        if not entity.id:
            raise ValueError("Entity must have an ID to update")

        try:
            query = text(f"""
                UPDATE proposal_deliberations
                SET proposal_id = :proposal_id,
                    conference_id = :conference_id,
                    meeting_id = :meeting_id,
                    stage = :stage,
                    updated_at = CURRENT_TIMESTAMP
                WHERE id = :id
                RETURNING {_SELECT_COLUMNS}
            """)

            result = await self.session.execute(
                query,
                {
                    "id": entity.id,
                    "proposal_id": entity.proposal_id,
                    "conference_id": entity.conference_id,
                    "meeting_id": entity.meeting_id,
                    "stage": entity.stage,
                },
            )
            row = result.fetchone()
            await self.session.commit()

            if row:
                return self._dict_to_entity(self._row_to_dict(row))

            raise DatabaseError(
                f"ProposalDeliberation with ID {entity.id} not found",
                {"entity": entity},
            )

        except SQLAlchemyError as e:
            logger.error(f"Database error updating proposal_deliberation: {e}")
            await self.session.rollback()
            raise DatabaseError(
                "Failed to update proposal_deliberation",
                {"entity": entity, "error": str(e)},
            ) from e

    async def delete(self, entity_id: int) -> bool:
        try:
            query = text("DELETE FROM proposal_deliberations WHERE id = :id")
            result = await self.session.execute(query, {"id": entity_id})
            await self.session.commit()

            return result.rowcount > 0  # type: ignore[attr-defined]

        except SQLAlchemyError as e:
            logger.error(f"Database error deleting proposal_deliberation: {e}")
            await self.session.rollback()
            raise DatabaseError(
                "Failed to delete proposal_deliberation",
                {"id": entity_id, "error": str(e)},
            ) from e

    async def count(self) -> int:
        try:
            query = text("SELECT COUNT(*) FROM proposal_deliberations")
            result = await self.session.execute(query)
            count = result.scalar()
            return count if count is not None else 0

        except SQLAlchemyError as e:
            logger.error(f"Database error counting proposal_deliberations: {e}")
            raise DatabaseError(
                "Failed to count proposal_deliberations", {"error": str(e)}
            ) from e

    async def get_by_proposal_id(self, proposal_id: int) -> list[ProposalDeliberation]:
        try:
            query = text(f"""
                SELECT {_SELECT_COLUMNS}
                FROM proposal_deliberations
                WHERE proposal_id = :proposal_id
                ORDER BY created_at DESC
            """)

            result = await self.session.execute(query, {"proposal_id": proposal_id})
            rows = result.fetchall()

            return [self._dict_to_entity(self._row_to_dict(row)) for row in rows]

        except SQLAlchemyError as e:
            logger.error(f"Database error getting deliberations by proposal_id: {e}")
            raise DatabaseError(
                "Failed to get deliberations by proposal_id",
                {"proposal_id": proposal_id, "error": str(e)},
            ) from e

    async def get_by_conference_id(
        self, conference_id: int
    ) -> list[ProposalDeliberation]:
        try:
            query = text(f"""
                SELECT {_SELECT_COLUMNS}
                FROM proposal_deliberations
                WHERE conference_id = :conference_id
                ORDER BY created_at DESC
            """)

            result = await self.session.execute(query, {"conference_id": conference_id})
            rows = result.fetchall()

            return [self._dict_to_entity(self._row_to_dict(row)) for row in rows]

        except SQLAlchemyError as e:
            logger.error(f"Database error getting deliberations by conference_id: {e}")
            raise DatabaseError(
                "Failed to get deliberations by conference_id",
                {"conference_id": conference_id, "error": str(e)},
            ) from e

    async def get_by_meeting_id(self, meeting_id: int) -> list[ProposalDeliberation]:
        try:
            query = text(f"""
                SELECT {_SELECT_COLUMNS}
                FROM proposal_deliberations
                WHERE meeting_id = :meeting_id
                ORDER BY created_at DESC
            """)

            result = await self.session.execute(query, {"meeting_id": meeting_id})
            rows = result.fetchall()

            return [self._dict_to_entity(self._row_to_dict(row)) for row in rows]

        except SQLAlchemyError as e:
            logger.error(f"Database error getting deliberations by meeting_id: {e}")
            raise DatabaseError(
                "Failed to get deliberations by meeting_id",
                {"meeting_id": meeting_id, "error": str(e)},
            ) from e

    async def find_by_proposal_and_conference(
        self,
        proposal_id: int,
        conference_id: int,
        meeting_id: int | None = None,
        stage: str | None = None,
    ) -> ProposalDeliberation | None:
        try:
            where_clauses = [
                "proposal_id = :proposal_id",
                "conference_id = :conference_id",
            ]
            params: dict[str, Any] = {
                "proposal_id": proposal_id,
                "conference_id": conference_id,
            }

            if meeting_id is not None:
                where_clauses.append("meeting_id = :meeting_id")
                params["meeting_id"] = meeting_id
            else:
                where_clauses.append("meeting_id IS NULL")

            if stage is not None:
                where_clauses.append("stage = :stage")
                params["stage"] = stage
            else:
                where_clauses.append("stage IS NULL")

            where_sql = " AND ".join(where_clauses)

            query = text(f"""
                SELECT {_SELECT_COLUMNS}
                FROM proposal_deliberations
                WHERE {where_sql}
            """)

            result = await self.session.execute(query, params)
            row = result.fetchone()

            if row:
                return self._dict_to_entity(self._row_to_dict(row))
            return None

        except SQLAlchemyError as e:
            logger.error(
                f"Database error finding deliberation by proposal and conference: {e}"
            )
            raise DatabaseError(
                "Failed to find deliberation by proposal and conference",
                {
                    "proposal_id": proposal_id,
                    "conference_id": conference_id,
                    "error": str(e),
                },
            ) from e
