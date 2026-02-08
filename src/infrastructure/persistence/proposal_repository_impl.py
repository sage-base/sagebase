"""Proposal repository implementation using SQLAlchemy."""

import logging

from datetime import datetime
from typing import Any

from pydantic import BaseModel as PydanticBaseModel
from sqlalchemy import text
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.ext.asyncio import AsyncSession

from src.domain.entities.proposal import Proposal
from src.domain.repositories.proposal_repository import ProposalRepository
from src.domain.repositories.session_adapter import ISessionAdapter
from src.infrastructure.exceptions import DatabaseError
from src.infrastructure.persistence.base_repository_impl import BaseRepositoryImpl


logger = logging.getLogger(__name__)


class ProposalModel(PydanticBaseModel):
    """Proposal database model."""

    id: int | None = None
    title: str
    detail_url: str | None = None
    status_url: str | None = None
    votes_url: str | None = None
    meeting_id: int | None = None
    conference_id: int | None = None
    proposal_category: str | None = None
    proposal_type: str | None = None
    governing_body_id: int | None = None
    session_number: int | None = None
    proposal_number: int | None = None
    external_id: str | None = None
    deliberation_status: str | None = None
    deliberation_result: str | None = None
    created_at: datetime | None = None
    updated_at: datetime | None = None

    class Config:
        arbitrary_types_allowed = True


_SELECT_COLUMNS = """
    id,
    title,
    detail_url,
    status_url,
    votes_url,
    meeting_id,
    conference_id,
    proposal_category,
    proposal_type,
    governing_body_id,
    session_number,
    proposal_number,
    external_id,
    deliberation_status,
    deliberation_result,
    created_at,
    updated_at
"""


class ProposalRepositoryImpl(BaseRepositoryImpl[Proposal], ProposalRepository):
    """Proposal repository implementation using SQLAlchemy."""

    def __init__(self, session: AsyncSession | ISessionAdapter):
        """Initialize repository with database session.

        Args:
            session: AsyncSession or ISessionAdapter for database operations
        """
        super().__init__(
            session=session,
            entity_class=Proposal,
            model_class=ProposalModel,
        )

    async def get_all(
        self, limit: int | None = None, offset: int | None = 0
    ) -> list[Proposal]:
        """Get all proposals.

        Args:
            limit: Maximum number of results
            offset: Number of results to skip

        Returns:
            List of Proposal entities
        """
        try:
            query_text = f"""
                SELECT {_SELECT_COLUMNS}
                FROM proposals
                ORDER BY created_at DESC
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
            logger.error(f"Database error getting all proposals: {e}")
            raise DatabaseError("Failed to get all proposals", {"error": str(e)}) from e

    async def get_by_id(self, entity_id: int) -> Proposal | None:
        """Get proposal by ID.

        Args:
            entity_id: Proposal ID

        Returns:
            Proposal entity or None if not found
        """
        try:
            query = text(f"""
                SELECT {_SELECT_COLUMNS}
                FROM proposals
                WHERE id = :id
            """)

            result = await self.session.execute(query, {"id": entity_id})
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
            logger.error(f"Database error getting proposal by ID: {e}")
            raise DatabaseError(
                "Failed to get proposal by ID",
                {"id": entity_id, "error": str(e)},
            ) from e

    async def create(self, entity: Proposal) -> Proposal:
        """Create a new proposal.

        Args:
            entity: Proposal entity to create

        Returns:
            Created Proposal entity with ID
        """
        try:
            query = text(f"""
                INSERT INTO proposals (
                    title, detail_url, status_url, votes_url,
                    meeting_id, conference_id,
                    proposal_category, proposal_type, governing_body_id,
                    session_number, proposal_number, external_id,
                    deliberation_status, deliberation_result
                )
                VALUES (
                    :title, :detail_url, :status_url, :votes_url,
                    :meeting_id, :conference_id,
                    :proposal_category, :proposal_type, :governing_body_id,
                    :session_number, :proposal_number, :external_id,
                    :deliberation_status, :deliberation_result
                )
                RETURNING {_SELECT_COLUMNS}
            """)

            result = await self.session.execute(
                query,
                {
                    "title": entity.title,
                    "detail_url": entity.detail_url,
                    "status_url": entity.status_url,
                    "votes_url": entity.votes_url,
                    "meeting_id": entity.meeting_id,
                    "conference_id": entity.conference_id,
                    "proposal_category": entity.proposal_category,
                    "proposal_type": entity.proposal_type,
                    "governing_body_id": entity.governing_body_id,
                    "session_number": entity.session_number,
                    "proposal_number": entity.proposal_number,
                    "external_id": entity.external_id,
                    "deliberation_status": entity.deliberation_status,
                    "deliberation_result": entity.deliberation_result,
                },
            )
            row = result.fetchone()
            await self.session.commit()

            if row:
                if hasattr(row, "_asdict"):
                    row_dict = row._asdict()  # type: ignore[attr-defined]
                elif hasattr(row, "_mapping"):
                    row_dict = dict(row._mapping)  # type: ignore[attr-defined]
                else:
                    row_dict = dict(row)
                return self._dict_to_entity(row_dict)

            raise DatabaseError("Failed to create proposal", {"entity": entity})

        except SQLAlchemyError as e:
            logger.error(f"Database error creating proposal: {e}")
            await self.session.rollback()
            raise DatabaseError(
                "Failed to create proposal", {"entity": entity, "error": str(e)}
            ) from e

    async def update(self, entity: Proposal) -> Proposal:
        """Update an existing proposal.

        Args:
            entity: Proposal entity with updated values

        Returns:
            Updated Proposal entity
        """
        if not entity.id:
            raise ValueError("Entity must have an ID to update")

        try:
            query = text(f"""
                UPDATE proposals
                SET title = :title,
                    detail_url = :detail_url,
                    status_url = :status_url,
                    votes_url = :votes_url,
                    meeting_id = :meeting_id,
                    conference_id = :conference_id,
                    proposal_category = :proposal_category,
                    proposal_type = :proposal_type,
                    governing_body_id = :governing_body_id,
                    session_number = :session_number,
                    proposal_number = :proposal_number,
                    external_id = :external_id,
                    deliberation_status = :deliberation_status,
                    deliberation_result = :deliberation_result,
                    updated_at = CURRENT_TIMESTAMP
                WHERE id = :id
                RETURNING {_SELECT_COLUMNS}
            """)

            result = await self.session.execute(
                query,
                {
                    "id": entity.id,
                    "title": entity.title,
                    "detail_url": entity.detail_url,
                    "status_url": entity.status_url,
                    "votes_url": entity.votes_url,
                    "meeting_id": entity.meeting_id,
                    "conference_id": entity.conference_id,
                    "proposal_category": entity.proposal_category,
                    "proposal_type": entity.proposal_type,
                    "governing_body_id": entity.governing_body_id,
                    "session_number": entity.session_number,
                    "proposal_number": entity.proposal_number,
                    "external_id": entity.external_id,
                    "deliberation_status": entity.deliberation_status,
                    "deliberation_result": entity.deliberation_result,
                },
            )
            row = result.fetchone()
            await self.session.commit()

            if row:
                if hasattr(row, "_asdict"):
                    row_dict = row._asdict()  # type: ignore[attr-defined]
                elif hasattr(row, "_mapping"):
                    row_dict = dict(row._mapping)  # type: ignore[attr-defined]
                else:
                    row_dict = dict(row)
                return self._dict_to_entity(row_dict)

            raise DatabaseError(
                f"Proposal with ID {entity.id} not found", {"entity": entity}
            )

        except SQLAlchemyError as e:
            logger.error(f"Database error updating proposal: {e}")
            await self.session.rollback()
            raise DatabaseError(
                "Failed to update proposal", {"entity": entity, "error": str(e)}
            ) from e

    async def delete(self, entity_id: int) -> bool:
        """Delete a proposal by ID.

        Args:
            entity_id: Proposal ID to delete

        Returns:
            True if deleted, False otherwise
        """
        try:
            # Check if there are related records
            check_query = text("""
                SELECT COUNT(*) FROM proposal_judges WHERE proposal_id = :proposal_id
            """)
            result = await self.session.execute(check_query, {"proposal_id": entity_id})
            count = result.scalar()

            if count and count > 0:
                return False  # Cannot delete if there are related judges

            query = text("DELETE FROM proposals WHERE id = :id")
            result = await self.session.execute(query, {"id": entity_id})
            await self.session.commit()

            return result.rowcount > 0  # type: ignore[attr-defined]

        except SQLAlchemyError as e:
            logger.error(f"Database error deleting proposal: {e}")
            await self.session.rollback()
            raise DatabaseError(
                "Failed to delete proposal", {"id": entity_id, "error": str(e)}
            ) from e

    def _to_entity(self, model: ProposalModel) -> Proposal:
        """Convert database model to domain entity.

        Args:
            model: Database model

        Returns:
            Domain entity
        """
        return Proposal(
            id=model.id,
            title=model.title,
            detail_url=model.detail_url,
            status_url=model.status_url,
            votes_url=model.votes_url,
            meeting_id=model.meeting_id,
            conference_id=model.conference_id,
            proposal_category=model.proposal_category,
            proposal_type=model.proposal_type,
            governing_body_id=model.governing_body_id,
            session_number=model.session_number,
            proposal_number=model.proposal_number,
            external_id=model.external_id,
            deliberation_status=model.deliberation_status,
            deliberation_result=model.deliberation_result,
        )

    def _to_model(self, entity: Proposal) -> ProposalModel:
        """Convert domain entity to database model.

        Args:
            entity: Domain entity

        Returns:
            Database model
        """
        return ProposalModel(
            id=entity.id,
            title=entity.title,
            detail_url=entity.detail_url,
            status_url=entity.status_url,
            votes_url=entity.votes_url,
            meeting_id=entity.meeting_id,
            conference_id=entity.conference_id,
            proposal_category=entity.proposal_category,
            proposal_type=entity.proposal_type,
            governing_body_id=entity.governing_body_id,
            session_number=entity.session_number,
            proposal_number=entity.proposal_number,
            external_id=entity.external_id,
            deliberation_status=entity.deliberation_status,
            deliberation_result=entity.deliberation_result,
        )

    def _update_model(self, model: ProposalModel, entity: Proposal) -> None:
        """Update model from entity.

        Args:
            model: Database model to update
            entity: Source entity
        """
        model.title = entity.title
        model.detail_url = entity.detail_url
        model.status_url = entity.status_url
        model.votes_url = entity.votes_url
        model.meeting_id = entity.meeting_id
        model.conference_id = entity.conference_id
        model.proposal_category = entity.proposal_category
        model.proposal_type = entity.proposal_type
        model.governing_body_id = entity.governing_body_id
        model.session_number = entity.session_number
        model.proposal_number = entity.proposal_number
        model.external_id = entity.external_id
        model.deliberation_status = entity.deliberation_status
        model.deliberation_result = entity.deliberation_result

    def _dict_to_entity(self, data: dict[str, Any]) -> Proposal:
        """Convert dictionary to entity.

        Args:
            data: Dictionary with entity data

        Returns:
            Proposal entity
        """
        return Proposal(
            id=data.get("id"),
            title=data["title"],
            detail_url=data.get("detail_url"),
            status_url=data.get("status_url"),
            votes_url=data.get("votes_url"),
            meeting_id=data.get("meeting_id"),
            conference_id=data.get("conference_id"),
            proposal_category=data.get("proposal_category"),
            proposal_type=data.get("proposal_type"),
            governing_body_id=data.get("governing_body_id"),
            session_number=data.get("session_number"),
            proposal_number=data.get("proposal_number"),
            external_id=data.get("external_id"),
            deliberation_status=data.get("deliberation_status"),
            deliberation_result=data.get("deliberation_result"),
        )

    async def get_by_meeting_id(self, meeting_id: int) -> list[Proposal]:
        """Get proposals by meeting ID.

        Args:
            meeting_id: Meeting ID to filter by

        Returns:
            List of proposals associated with the specified meeting
        """
        try:
            query = text(f"""
                SELECT {_SELECT_COLUMNS}
                FROM proposals
                WHERE meeting_id = :meeting_id
                ORDER BY created_at DESC
            """)

            result = await self.session.execute(query, {"meeting_id": meeting_id})
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
            logger.error(f"Database error getting proposals by meeting ID: {e}")
            raise DatabaseError(
                "Failed to get proposals by meeting ID",
                {"meeting_id": meeting_id, "error": str(e)},
            ) from e

    async def get_by_conference_id(self, conference_id: int) -> list[Proposal]:
        """Get proposals by conference ID.

        Args:
            conference_id: Conference ID to filter by

        Returns:
            List of proposals associated with the specified conference
        """
        try:
            query = text(f"""
                SELECT {_SELECT_COLUMNS}
                FROM proposals
                WHERE conference_id = :conference_id
                ORDER BY created_at DESC
            """)

            result = await self.session.execute(query, {"conference_id": conference_id})
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
            logger.error(f"Database error getting proposals by conference ID: {e}")
            raise DatabaseError(
                "Failed to get proposals by conference ID",
                {"conference_id": conference_id, "error": str(e)},
            ) from e

    async def find_by_url(self, url: str) -> Proposal | None:
        """Find proposal by URL (detail_url, status_url, or votes_url).

        Args:
            url: URL of the proposal

        Returns:
            Proposal if found, None otherwise

        Raises:
            DatabaseError: If database operation fails
        """
        try:
            query = text(f"""
                SELECT {_SELECT_COLUMNS}
                FROM proposals
                WHERE detail_url = :url OR status_url = :url OR votes_url = :url
            """)
            result = await self.session.execute(query, {"url": url})
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
            logger.error(f"Database error finding proposal by URL: {e}")
            raise DatabaseError(
                "Failed to find proposal by URL",
                {"url": url, "error": str(e)},
            ) from e

    async def find_by_identifier(
        self,
        governing_body_id: int,
        session_number: int,
        proposal_number: int,
        proposal_type: str,
    ) -> Proposal | None:
        """Find proposal by unique identifier combination.

        Args:
            governing_body_id: Governing body ID
            session_number: Session number
            proposal_number: Proposal number
            proposal_type: Proposal type

        Returns:
            Proposal if found, None otherwise

        Raises:
            DatabaseError: If database operation fails
        """
        try:
            query = text(f"""
                SELECT {_SELECT_COLUMNS}
                FROM proposals
                WHERE governing_body_id = :governing_body_id
                    AND session_number = :session_number
                    AND proposal_number = :proposal_number
                    AND proposal_type = :proposal_type
            """)
            result = await self.session.execute(
                query,
                {
                    "governing_body_id": governing_body_id,
                    "session_number": session_number,
                    "proposal_number": proposal_number,
                    "proposal_type": proposal_type,
                },
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
            logger.error(f"Database error finding proposal by identifier: {e}")
            raise DatabaseError(
                "Failed to find proposal by identifier",
                {
                    "governing_body_id": governing_body_id,
                    "session_number": session_number,
                    "proposal_number": proposal_number,
                    "proposal_type": proposal_type,
                    "error": str(e),
                },
            ) from e

    async def bulk_create(self, entities: list[Proposal]) -> list[Proposal]:
        """Create multiple proposals at once.

        Args:
            entities: List of Proposal entities to create

        Returns:
            List of created Proposal entities with IDs
        """
        if not entities:
            return []

        try:
            query = text(f"""
                INSERT INTO proposals (
                    title, detail_url, status_url, votes_url,
                    meeting_id, conference_id,
                    proposal_category, proposal_type, governing_body_id,
                    session_number, proposal_number, external_id,
                    deliberation_status, deliberation_result
                )
                VALUES (
                    :title, :detail_url, :status_url, :votes_url,
                    :meeting_id, :conference_id,
                    :proposal_category, :proposal_type, :governing_body_id,
                    :session_number, :proposal_number, :external_id,
                    :deliberation_status, :deliberation_result
                )
                RETURNING {_SELECT_COLUMNS}
            """)

            created_proposals = []
            for entity in entities:
                result = await self.session.execute(
                    query,
                    {
                        "title": entity.title,
                        "detail_url": entity.detail_url,
                        "status_url": entity.status_url,
                        "votes_url": entity.votes_url,
                        "meeting_id": entity.meeting_id,
                        "conference_id": entity.conference_id,
                        "proposal_category": entity.proposal_category,
                        "proposal_type": entity.proposal_type,
                        "governing_body_id": entity.governing_body_id,
                        "session_number": entity.session_number,
                        "proposal_number": entity.proposal_number,
                        "external_id": entity.external_id,
                        "deliberation_status": entity.deliberation_status,
                        "deliberation_result": entity.deliberation_result,
                    },
                )
                row = result.fetchone()
                if row:
                    if hasattr(row, "_asdict"):
                        row_dict = row._asdict()  # type: ignore[attr-defined]
                    elif hasattr(row, "_mapping"):
                        row_dict = dict(row._mapping)  # type: ignore[attr-defined]
                    else:
                        row_dict = dict(row)
                    created_proposals.append(self._dict_to_entity(row_dict))

            await self.session.commit()
            return created_proposals

        except SQLAlchemyError as e:
            logger.error(f"Database error bulk creating proposals: {e}")
            await self.session.rollback()
            raise DatabaseError(
                "Failed to bulk create proposals",
                {"count": len(entities), "error": str(e)},
            ) from e
