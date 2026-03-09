"""ExtractedParliamentaryGroupMember repository implementation using SQLAlchemy."""

from datetime import datetime
from typing import Any

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from src.domain.entities.extracted_parliamentary_group_member import (
    ExtractedParliamentaryGroupMember,
)
from src.domain.repositories.extracted_parliamentary_group_member_repository import (
    ExtractedParliamentaryGroupMemberRepository as IExtractedParliamentaryGroupMemberRepository,  # noqa: E501
)
from src.domain.repositories.session_adapter import ISessionAdapter
from src.infrastructure.persistence.base_repository_impl import BaseRepositoryImpl
from src.infrastructure.persistence.sqlalchemy_models import (
    ExtractedParliamentaryGroupMemberModel,
)


class ExtractedParliamentaryGroupMemberRepositoryImpl(
    BaseRepositoryImpl[ExtractedParliamentaryGroupMember],
    IExtractedParliamentaryGroupMemberRepository,
):
    """ExtractedParliamentaryGroupMemberRepository implementation using SQLAlchemy."""

    def __init__(self, session: AsyncSession | ISessionAdapter):
        super().__init__(
            session,
            ExtractedParliamentaryGroupMember,
            ExtractedParliamentaryGroupMemberModel,
        )

    async def get_by_id(
        self, entity_id: int
    ) -> ExtractedParliamentaryGroupMember | None:
        """Get extracted member by ID."""
        model = await self.session.get(self.model_class, entity_id)
        if model:
            return self._to_entity(model)
        return None

    async def get_all(
        self, limit: int | None = None, offset: int | None = None
    ) -> list[ExtractedParliamentaryGroupMember]:
        """Get all extracted members."""
        query_str = "SELECT * FROM extracted_parliamentary_group_members"

        if limit is not None or offset is not None:
            query_str += " LIMIT :limit OFFSET :offset"
            params = {"limit": limit or 10000, "offset": offset or 0}
        else:
            params = {}

        query = text(query_str)
        result = await self.session.execute(query, params)
        rows = result.fetchall()

        return [self._to_entity(row) for row in rows]

    async def get_pending_members(
        self, parliamentary_group_id: int | None = None
    ) -> list[ExtractedParliamentaryGroupMember]:
        """Get all pending members for matching."""
        conditions = ["matching_status = 'pending'"]
        params: dict[str, Any] = {}

        if parliamentary_group_id is not None:
            conditions.append("parliamentary_group_id = :group_id")
            params["group_id"] = parliamentary_group_id

        query = text(f"""
            SELECT * FROM extracted_parliamentary_group_members
            WHERE {" AND ".join(conditions)}
            ORDER BY extracted_at DESC
        """)

        result = await self.session.execute(query, params)
        rows = result.fetchall()

        return [self._to_entity(row) for row in rows]

    async def get_matched_members(
        self,
        parliamentary_group_id: int | None = None,
        min_confidence: float | None = None,
    ) -> list[ExtractedParliamentaryGroupMember]:
        """Get matched members with optional filtering."""
        conditions = ["matching_status = 'matched'"]
        params: dict[str, Any] = {}

        if parliamentary_group_id is not None:
            conditions.append("parliamentary_group_id = :group_id")
            params["group_id"] = parliamentary_group_id

        if min_confidence is not None:
            conditions.append("matching_confidence >= :min_conf")
            params["min_conf"] = min_confidence

        query = text(f"""
            SELECT * FROM extracted_parliamentary_group_members
            WHERE {" AND ".join(conditions)}
            ORDER BY matching_confidence DESC
        """)

        result = await self.session.execute(query, params)
        rows = result.fetchall()

        return [self._to_entity(row) for row in rows]

    async def update_matching_result(
        self,
        member_id: int,
        politician_id: int | None,
        confidence: float | None,
        status: str,
        matched_at: datetime | None = None,
    ) -> ExtractedParliamentaryGroupMember | None:
        """Update the matching result for a member."""
        query = text("""
            UPDATE extracted_parliamentary_group_members
            SET matched_politician_id = :pol_id,
                matching_confidence = :confidence,
                matching_status = :status,
                matched_at = :matched_at
            WHERE id = :member_id
        """)

        await self.session.execute(
            query,
            {
                "member_id": member_id,
                "pol_id": politician_id,
                "confidence": confidence,
                "status": status,
                "matched_at": matched_at or datetime.now(),
            },
        )
        await self.session.flush()  # Flush changes but don't commit

        # Return updated entity
        return await self.get_by_id(member_id)

    async def get_by_parliamentary_group(
        self, parliamentary_group_id: int
    ) -> list[ExtractedParliamentaryGroupMember]:
        """Get all extracted members for a parliamentary group."""
        query = text("""
            SELECT * FROM extracted_parliamentary_group_members
            WHERE parliamentary_group_id = :group_id
            ORDER BY extracted_name
        """)

        result = await self.session.execute(query, {"group_id": parliamentary_group_id})
        rows = result.fetchall()

        return [self._to_entity(row) for row in rows]

    async def get_extraction_summary(
        self, parliamentary_group_id: int | None = None
    ) -> dict[str, int]:
        """Get summary statistics for extracted members."""
        where_clause = ""
        params: dict[str, Any] = {}

        if parliamentary_group_id is not None:
            where_clause = "WHERE parliamentary_group_id = :group_id"
            params["group_id"] = parliamentary_group_id

        query = text(f"""
            SELECT matching_status, COUNT(*) as count
            FROM extracted_parliamentary_group_members
            {where_clause}
            GROUP BY matching_status
        """)

        result = await self.session.execute(query, params)
        rows = result.fetchall()

        summary = {
            "total": 0,
            "pending": 0,
            "matched": 0,
            "no_match": 0,
        }

        for row in rows:
            status = row.matching_status
            count = getattr(row, "count", 0)  # Use getattr to access the count
            if status in summary:
                summary[status] = count
            summary["total"] += count

        return summary

    async def bulk_create(
        self, members: list[ExtractedParliamentaryGroupMember]
    ) -> list[ExtractedParliamentaryGroupMember]:
        """Create multiple extracted members at once, skipping duplicates."""
        from sqlalchemy.exc import IntegrityError

        # SQLAlchemy models are not used directly here, we use raw SQL
        created_members = []
        for member in members:
            try:
                query = text("""
                    INSERT INTO extracted_parliamentary_group_members (
                        parliamentary_group_id, extracted_name, source_url,
                        extracted_role, extracted_party_name, extracted_district,
                        extracted_at, matching_status, additional_info
                    )
                    VALUES (
                        :group_id, :name, :url,
                        :role, :party, :district,
                        :extracted_at, :status, :info
                    )
                    ON CONFLICT (parliamentary_group_id, extracted_name)
                    DO NOTHING
                    RETURNING *
                """)

                result = await self.session.execute(
                    query,
                    {
                        "group_id": member.parliamentary_group_id,
                        "name": member.extracted_name,
                        "url": member.source_url,
                        "role": member.extracted_role,
                        "party": member.extracted_party_name,
                        "district": member.extracted_district,
                        "extracted_at": member.extracted_at,
                        "status": member.matching_status,
                        "info": member.additional_info,
                    },
                )
                row = result.fetchone()
                if row:
                    created_members.append(self._to_entity(row))

            except IntegrityError:
                # In case of any integrity error, just skip this member
                continue

        await self.session.flush()  # Flush changes but don't commit
        return created_members

    async def save_extracted_members(
        self,
        parliamentary_group_id: int,
        members: list[Any],
        url: str,
    ) -> int:
        """Save extracted members, preventing duplicates based on group + name.

        Args:
            parliamentary_group_id: The parliamentary group ID
            members: List of ExtractedMember objects from extraction
            url: Source URL for the extraction

        Returns:
            Number of members actually saved (excluding duplicates)
        """
        from datetime import datetime

        from sqlalchemy.exc import IntegrityError

        saved_count = 0

        for member in members:
            try:
                # Use INSERT ... ON CONFLICT DO NOTHING to handle race conditions
                insert_query = text("""
                    INSERT INTO extracted_parliamentary_group_members (
                        parliamentary_group_id, extracted_name, source_url,
                        extracted_role, extracted_party_name, extracted_district,
                        extracted_at, matching_status, additional_info
                    )
                    VALUES (
                        :group_id, :name, :url,
                        :role, :party, :district,
                        :extracted_at, :status, :info
                    )
                    ON CONFLICT (parliamentary_group_id, extracted_name)
                    DO NOTHING
                    RETURNING id
                """)

                result = await self.session.execute(
                    insert_query,
                    {
                        "group_id": parliamentary_group_id,
                        "name": member.name,
                        "url": url,
                        "role": member.role,
                        "party": member.party_name,
                        "district": member.district,
                        "extracted_at": datetime.now(),
                        "status": "pending",
                        "info": member.additional_info
                        if hasattr(member, "additional_info")
                        else None,
                    },
                )

                # Check if a row was actually inserted
                inserted = result.fetchone()
                if inserted:
                    saved_count += 1

            except IntegrityError:
                # In case of any integrity error, just skip this member
                continue

        await self.session.flush()
        return saved_count

    def _to_entity(self, model: Any) -> ExtractedParliamentaryGroupMember:
        """Convert database model to domain entity."""
        return ExtractedParliamentaryGroupMember(
            id=model.id,
            parliamentary_group_id=model.parliamentary_group_id,
            extracted_name=model.extracted_name,
            source_url=model.source_url,
            extracted_role=model.extracted_role,
            extracted_party_name=model.extracted_party_name,
            extracted_district=getattr(model, "extracted_district", None),
            extracted_at=model.extracted_at,
            matched_politician_id=model.matched_politician_id,
            matching_confidence=model.matching_confidence,
            matching_status=model.matching_status,
            matched_at=model.matched_at,
            additional_info=getattr(model, "additional_info", None),
        )

    def _to_model(
        self, entity: ExtractedParliamentaryGroupMember
    ) -> ExtractedParliamentaryGroupMemberModel:
        """Convert domain entity to database model."""
        data = {
            "parliamentary_group_id": entity.parliamentary_group_id,
            "extracted_name": entity.extracted_name,
            "source_url": entity.source_url,
            "extracted_role": entity.extracted_role,
            "extracted_party_name": entity.extracted_party_name,
            "extracted_district": entity.extracted_district,
            "extracted_at": entity.extracted_at,
            "matched_politician_id": entity.matched_politician_id,
            "matching_confidence": entity.matching_confidence,
            "matching_status": entity.matching_status,
            "matched_at": entity.matched_at,
        }

        if hasattr(entity, "additional_info") and entity.additional_info is not None:
            data["additional_info"] = entity.additional_info
        if entity.id is not None:
            data["id"] = entity.id

        return ExtractedParliamentaryGroupMemberModel(**data)

    def _update_model(
        self,
        model: ExtractedParliamentaryGroupMemberModel,
        entity: ExtractedParliamentaryGroupMember,
    ) -> None:
        """Update model fields from entity."""
        # Validate required fields
        if not entity.extracted_name or not entity.source_url:
            raise ValueError(
                "Required fields (extracted_name, source_url) must not be empty"
            )

        model.parliamentary_group_id = entity.parliamentary_group_id
        model.extracted_name = entity.extracted_name
        model.source_url = entity.source_url
        model.extracted_role = entity.extracted_role
        model.extracted_party_name = entity.extracted_party_name
        model.extracted_district = entity.extracted_district
        model.extracted_at = entity.extracted_at
        model.matched_politician_id = entity.matched_politician_id
        model.matching_confidence = entity.matching_confidence
        model.matching_status = entity.matching_status
        model.matched_at = entity.matched_at

        if hasattr(entity, "additional_info") and entity.additional_info is not None:
            model.additional_info = entity.additional_info
