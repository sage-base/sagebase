"""ExtractedConferenceMember repository implementation using SQLAlchemy."""

from typing import Any

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from src.domain.entities.extracted_conference_member import ExtractedConferenceMember
from src.domain.repositories.extracted_conference_member_repository import (
    ExtractedConferenceMemberRepository as IExtractedConferenceMemberRepository,
)
from src.domain.repositories.session_adapter import ISessionAdapter
from src.infrastructure.persistence.base_repository_impl import BaseRepositoryImpl


class ExtractedConferenceMemberModel:
    """Extracted conference member database model (dynamic).

    Bronze Layer（抽出ログ層）のモデル。
    政治家との紐付け情報はGold Layer（ConferenceMember）に移行済み。
    """

    id: int | None
    conference_id: int
    extracted_name: str
    source_url: str
    extracted_role: str | None
    extracted_party_name: str | None
    extracted_at: Any  # datetime
    additional_data: str | None

    def __init__(self, **kwargs: Any):
        for key, value in kwargs.items():
            setattr(self, key, value)


class ExtractedConferenceMemberRepositoryImpl(
    BaseRepositoryImpl[ExtractedConferenceMember], IExtractedConferenceMemberRepository
):
    """Implementation of ExtractedConferenceMemberRepository using SQLAlchemy."""

    def __init__(self, session: AsyncSession | ISessionAdapter):
        super().__init__(
            session, ExtractedConferenceMember, ExtractedConferenceMemberModel
        )

    async def get_by_id(self, entity_id: int) -> ExtractedConferenceMember | None:
        """Get extracted member by ID."""
        query = text("""
            SELECT * FROM extracted_conference_members
            WHERE id = :id
        """)
        result = await self.session.execute(query, {"id": entity_id})
        row = result.fetchone()
        return self._row_to_entity(row) if row else None

    async def get_all(
        self, limit: int | None = None, offset: int | None = None
    ) -> list[ExtractedConferenceMember]:
        """Get all extracted members with optional pagination."""
        query_str = (
            "SELECT * FROM extracted_conference_members ORDER BY extracted_at DESC"
        )

        if limit:
            query_str += f" LIMIT {limit}"
        if offset:
            query_str += f" OFFSET {offset}"

        query = text(query_str)
        result = await self.session.execute(query)
        rows = result.fetchall()

        return [self._row_to_entity(row) for row in rows]

    async def create(
        self, entity: ExtractedConferenceMember
    ) -> ExtractedConferenceMember:
        """Create a new extracted member."""
        query = text("""
            INSERT INTO extracted_conference_members (
                conference_id, extracted_name, source_url,
                extracted_role, extracted_party_name,
                extracted_at, additional_info
            ) VALUES (
                :conference_id, :extracted_name, :source_url,
                :extracted_role, :extracted_party_name,
                :extracted_at, :additional_info
            ) RETURNING id
        """)

        result = await self.session.execute(
            query,
            {
                "conference_id": entity.conference_id,
                "extracted_name": entity.extracted_name,
                "source_url": entity.source_url,
                "extracted_role": entity.extracted_role,
                "extracted_party_name": entity.extracted_party_name,
                "extracted_at": entity.extracted_at,
                "additional_info": entity.additional_data,
            },
        )
        await self.session.commit()

        row = result.fetchone()
        if row:
            entity.id = row.id
        return entity

    async def update(
        self, entity: ExtractedConferenceMember
    ) -> ExtractedConferenceMember:
        """Update an existing extracted member."""
        if not entity.id:
            raise ValueError("Entity must have an ID to update")

        query = text("""
            UPDATE extracted_conference_members
            SET conference_id = :conference_id,
                extracted_name = :extracted_name,
                source_url = :source_url,
                extracted_role = :extracted_role,
                extracted_party_name = :extracted_party_name,
                additional_info = :additional_info
            WHERE id = :id
        """)

        await self.session.execute(
            query,
            {
                "id": entity.id,
                "conference_id": entity.conference_id,
                "extracted_name": entity.extracted_name,
                "source_url": entity.source_url,
                "extracted_role": entity.extracted_role,
                "extracted_party_name": entity.extracted_party_name,
                "additional_info": entity.additional_data,
            },
        )
        await self.session.commit()
        return entity

    async def delete(self, entity_id: int) -> bool:
        """Delete an extracted member by ID."""
        query = text("""
            DELETE FROM extracted_conference_members
            WHERE id = :id
        """)
        result = await self.session.execute(query, {"id": entity_id})
        await self.session.commit()
        return result.rowcount > 0

    async def count(self) -> int:
        """Count total number of extracted members."""
        query = text("""
            SELECT COUNT(*) FROM extracted_conference_members
        """)
        result = await self.session.execute(query)
        count = result.scalar()
        return count if count is not None else 0

    async def get_by_conference(
        self, conference_id: int
    ) -> list[ExtractedConferenceMember]:
        """Get all extracted members for a conference."""
        query = text("""
            SELECT * FROM extracted_conference_members
            WHERE conference_id = :conf_id
            ORDER BY extracted_name
        """)

        result = await self.session.execute(query, {"conf_id": conference_id})
        rows = result.fetchall()

        return [self._row_to_entity(row) for row in rows]

    async def get_extraction_summary(
        self, conference_id: int | None = None
    ) -> dict[str, int]:
        """Get summary statistics for extracted members.

        Returns:
            dict with 'total' key containing the count of members.
        """
        where_clause = ""
        params: dict[str, Any] = {}

        if conference_id is not None:
            where_clause = "WHERE conference_id = :conf_id"
            params["conf_id"] = conference_id

        query = text(f"""
            SELECT COUNT(*) as total
            FROM extracted_conference_members
            {where_clause}
        """)

        result = await self.session.execute(query, params)
        row = result.fetchone()

        total = getattr(row, "total", 0) if row else 0

        return {"total": total}

    async def bulk_create(
        self, members: list[ExtractedConferenceMember]
    ) -> list[ExtractedConferenceMember]:
        """Create multiple extracted members at once."""
        models = [self._to_model(member) for member in members]
        self.session.add_all(models)
        await self.session.commit()

        # Refresh all models to get IDs
        for model in models:
            await self.session.refresh(model)

        return [self._to_entity(model) for model in models]

    def _row_to_entity(self, row: Any) -> ExtractedConferenceMember:
        """Convert database row to domain entity."""
        return ExtractedConferenceMember(
            id=row.id,
            conference_id=row.conference_id,
            extracted_name=row.extracted_name,
            source_url=row.source_url,
            extracted_role=getattr(row, "extracted_role", None),
            extracted_party_name=getattr(row, "extracted_party_name", None),
            extracted_at=row.extracted_at,
            additional_data=getattr(row, "additional_data", None),
        )

    def _to_entity(
        self, model: ExtractedConferenceMemberModel
    ) -> ExtractedConferenceMember:
        """Convert database model to domain entity."""
        return ExtractedConferenceMember(
            id=model.id,
            conference_id=model.conference_id,
            extracted_name=model.extracted_name,
            source_url=model.source_url,
            extracted_role=model.extracted_role,
            extracted_party_name=model.extracted_party_name,
            extracted_at=model.extracted_at,
            additional_data=getattr(model, "additional_data", None),
        )

    def _to_model(
        self, entity: ExtractedConferenceMember
    ) -> ExtractedConferenceMemberModel:
        """Convert domain entity to database model."""
        data: dict[str, Any] = {
            "conference_id": entity.conference_id,
            "extracted_name": entity.extracted_name,
            "source_url": entity.source_url,
            "extracted_role": entity.extracted_role,
            "extracted_party_name": entity.extracted_party_name,
            "extracted_at": entity.extracted_at,
        }

        if hasattr(entity, "additional_data") and entity.additional_data is not None:
            data["additional_data"] = entity.additional_data
        if entity.id is not None:
            data["id"] = entity.id

        return ExtractedConferenceMemberModel(**data)

    def _update_model(
        self,
        model: ExtractedConferenceMemberModel,
        entity: ExtractedConferenceMember,
    ) -> None:
        """Update model fields from entity."""
        model.conference_id = entity.conference_id
        model.extracted_name = entity.extracted_name
        model.source_url = entity.source_url
        model.extracted_role = entity.extracted_role
        model.extracted_party_name = entity.extracted_party_name
        model.extracted_at = entity.extracted_at

        if hasattr(entity, "additional_data") and entity.additional_data is not None:
            model.additional_data = entity.additional_data
