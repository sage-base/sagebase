"""ExtractedProposalJudge repository implementation using SQLAlchemy."""

from datetime import datetime
from typing import Any

from pydantic import BaseModel as PydanticBaseModel
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from src.domain.entities.extracted_proposal_judge import ExtractedProposalJudge
from src.domain.entities.proposal_judge import ProposalJudge
from src.domain.repositories.extracted_proposal_judge_repository import (
    ExtractedProposalJudgeRepository as IExtractedProposalJudgeRepository,
)
from src.domain.repositories.session_adapter import ISessionAdapter
from src.infrastructure.persistence.base_repository_impl import BaseRepositoryImpl


class ExtractedProposalJudgeModel(PydanticBaseModel):
    """Extracted proposal judge database model."""

    id: int | None = None
    proposal_id: int
    extracted_politician_name: str | None = None
    extracted_party_name: str | None = None
    extracted_parliamentary_group_name: str | None = None
    extracted_judgment: str | None = None
    source_url: str | None = None
    extracted_at: datetime
    matched_politician_id: int | None = None
    matched_parliamentary_group_id: int | None = None
    matching_confidence: float | None = None
    matching_status: str = "pending"
    matched_at: datetime | None = None
    additional_data: str | None = None

    class Config:
        arbitrary_types_allowed = True


class ExtractedProposalJudgeRepositoryImpl(
    BaseRepositoryImpl[ExtractedProposalJudge], IExtractedProposalJudgeRepository
):
    """Implementation of ExtractedProposalJudgeRepository using SQLAlchemy."""

    def __init__(self, session: AsyncSession | ISessionAdapter):
        super().__init__(session, ExtractedProposalJudge, ExtractedProposalJudgeModel)

    async def get_by_id(self, entity_id: int) -> ExtractedProposalJudge | None:
        """Get entity by ID."""
        query = text("""
            SELECT * FROM extracted_proposal_judges WHERE id = :id
        """)
        result = await self.session.execute(query, {"id": entity_id})
        row = result.fetchone()
        if row:
            return self._to_entity(row)
        return None

    async def delete(self, entity_id: int) -> bool:
        """Delete an entity by ID."""
        query = text("""
            DELETE FROM extracted_proposal_judges WHERE id = :id
        """)

        await self.session.execute(query, {"id": entity_id})
        await self.session.commit()

        # rowcountは削除された行数を返す
        return True  # SQLAlchemy AsyncSessionではrowcountが使えないため、常にTrueを返す

    async def update(self, entity: ExtractedProposalJudge) -> ExtractedProposalJudge:
        """Update an existing entity."""
        if not entity.id:
            raise ValueError("Entity must have an ID to update")

        query = text("""
            UPDATE extracted_proposal_judges SET
                proposal_id = :proposal_id,
                extracted_politician_name = :extracted_politician_name,
                extracted_party_name = :extracted_party_name,
                extracted_parliamentary_group_name =
                    :extracted_parliamentary_group_name,
                extracted_judgment = :extracted_judgment,
                source_url = :source_url,
                matched_politician_id = :matched_politician_id,
                matched_parliamentary_group_id = :matched_parliamentary_group_id,
                matching_confidence = :matching_confidence,
                matching_status = :matching_status,
                matched_at = :matched_at,
                additional_data = :additional_data
            WHERE id = :id
            RETURNING id, proposal_id, extracted_politician_name,
                      extracted_party_name, extracted_parliamentary_group_name,
                      extracted_judgment, source_url, extracted_at,
                      matched_politician_id, matched_parliamentary_group_id,
                      matching_confidence, matching_status, matched_at,
                      additional_data
        """)

        params: dict[str, Any] = {
            "id": entity.id,
            "proposal_id": entity.proposal_id,
            "extracted_politician_name": entity.extracted_politician_name,
            "extracted_party_name": entity.extracted_party_name,
            "extracted_parliamentary_group_name": (
                entity.extracted_parliamentary_group_name
            ),
            "extracted_judgment": entity.extracted_judgment,
            "source_url": entity.source_url,
            "matched_politician_id": entity.matched_politician_id,
            "matched_parliamentary_group_id": entity.matched_parliamentary_group_id,
            "matching_confidence": entity.matching_confidence,
            "matching_status": entity.matching_status,
            "matched_at": entity.matched_at,
            "additional_data": (
                entity.additional_data if hasattr(entity, "additional_data") else None
            ),
        }

        result = await self.session.execute(query, params)
        row = result.fetchone()
        await self.session.commit()

        if row:
            return self._to_entity(row)
        raise RuntimeError("Failed to update extracted proposal judge")

    async def create(self, entity: ExtractedProposalJudge) -> ExtractedProposalJudge:
        """Create a new entity."""
        query = text("""
            INSERT INTO extracted_proposal_judges (
                proposal_id, extracted_politician_name, extracted_party_name,
                extracted_parliamentary_group_name, extracted_judgment, source_url,
                extracted_at, matched_politician_id, matched_parliamentary_group_id,
                matching_confidence, matching_status, matched_at, additional_data
            )
            VALUES (
                :proposal_id, :extracted_politician_name, :extracted_party_name,
                :extracted_parliamentary_group_name, :extracted_judgment, :source_url,
                :extracted_at, :matched_politician_id, :matched_parliamentary_group_id,
                :matching_confidence, :matching_status, :matched_at, :additional_data
            )
            RETURNING id, proposal_id, extracted_politician_name,
                      extracted_party_name, extracted_parliamentary_group_name,
                      extracted_judgment, source_url, extracted_at,
                      matched_politician_id, matched_parliamentary_group_id,
                      matching_confidence, matching_status, matched_at,
                      additional_data
        """)

        params: dict[str, Any] = {
            "proposal_id": entity.proposal_id,
            "extracted_politician_name": entity.extracted_politician_name,
            "extracted_party_name": entity.extracted_party_name,
            "extracted_parliamentary_group_name": (
                entity.extracted_parliamentary_group_name
            ),
            "extracted_judgment": entity.extracted_judgment,
            "source_url": entity.source_url,
            "extracted_at": entity.extracted_at,
            "matched_politician_id": entity.matched_politician_id,
            "matched_parliamentary_group_id": entity.matched_parliamentary_group_id,
            "matching_confidence": entity.matching_confidence,
            "matching_status": entity.matching_status,
            "matched_at": entity.matched_at,
            "additional_data": (
                entity.additional_data if hasattr(entity, "additional_data") else None
            ),
        }

        result = await self.session.execute(query, params)
        row = result.fetchone()
        await self.session.commit()

        if row:
            return self._to_entity(row)
        raise RuntimeError("Failed to create extracted proposal judge")

    async def get_all(
        self, limit: int | None = None, offset: int | None = None
    ) -> list[ExtractedProposalJudge]:
        """Get all extracted proposal judges with optional pagination."""
        query_str = "SELECT * FROM extracted_proposal_judges ORDER BY id"
        params: dict[str, Any] = {}

        if limit:
            query_str += " LIMIT :limit"
            params["limit"] = limit
        if offset:
            query_str += " OFFSET :offset"
            params["offset"] = offset

        query = text(query_str)
        result = await self.session.execute(query, params)
        rows = result.fetchall()

        return [self._to_entity(row) for row in rows]

    async def get_pending_judges(
        self, proposal_id: int | None = None
    ) -> list[ExtractedProposalJudge]:
        """Get all pending judges for matching."""
        conditions = ["matching_status = 'pending'"]
        params: dict[str, Any] = {}

        if proposal_id is not None:
            conditions.append("proposal_id = :prop_id")
            params["prop_id"] = proposal_id

        query = text(f"""
            SELECT * FROM extracted_proposal_judges
            WHERE {" AND ".join(conditions)}
            ORDER BY extracted_at DESC
        """)

        result = await self.session.execute(query, params)
        rows = result.fetchall()

        return [self._to_entity(row) for row in rows]

    async def get_matched_judges(
        self, proposal_id: int | None = None, min_confidence: float | None = None
    ) -> list[ExtractedProposalJudge]:
        """Get matched judges with optional filtering."""
        conditions = ["matching_status = 'matched'"]
        params: dict[str, Any] = {}

        if proposal_id is not None:
            conditions.append("proposal_id = :prop_id")
            params["prop_id"] = proposal_id

        if min_confidence is not None:
            conditions.append("matching_confidence >= :min_conf")
            params["min_conf"] = min_confidence

        query = text(f"""
            SELECT * FROM extracted_proposal_judges
            WHERE {" AND ".join(conditions)}
            ORDER BY matching_confidence DESC
        """)

        result = await self.session.execute(query, params)
        rows = result.fetchall()

        return [self._to_entity(row) for row in rows]

    async def get_needs_review_judges(
        self, proposal_id: int | None = None
    ) -> list[ExtractedProposalJudge]:
        """Get judges that need manual review."""
        conditions = ["matching_status = 'needs_review'"]
        params: dict[str, Any] = {}

        if proposal_id is not None:
            conditions.append("proposal_id = :prop_id")
            params["prop_id"] = proposal_id

        query = text(f"""
            SELECT * FROM extracted_proposal_judges
            WHERE {" AND ".join(conditions)}
            ORDER BY extracted_at DESC
        """)

        result = await self.session.execute(query, params)
        rows = result.fetchall()

        return [self._to_entity(row) for row in rows]

    async def update_matching_result(
        self,
        judge_id: int,
        politician_id: int | None = None,
        parliamentary_group_id: int | None = None,
        confidence: float | None = None,
        status: str = "pending",
    ) -> ExtractedProposalJudge | None:
        """Update the matching result for a judge."""
        query = text("""
            UPDATE extracted_proposal_judges
            SET matched_politician_id = :pol_id,
                matched_parliamentary_group_id = :group_id,
                matching_confidence = :confidence,
                matching_status = :status,
                matched_at = :matched_at
            WHERE id = :judge_id
        """)

        await self.session.execute(
            query,
            {
                "judge_id": judge_id,
                "pol_id": politician_id,
                "group_id": parliamentary_group_id,
                "confidence": confidence,
                "status": status,
                "matched_at": datetime.now(),
            },
        )
        await self.session.commit()

        # Return updated entity
        return await self.get_by_id(judge_id)

    async def get_by_proposal(self, proposal_id: int) -> list[ExtractedProposalJudge]:
        """Get all extracted judges for a proposal."""
        query = text("""
            SELECT * FROM extracted_proposal_judges
            WHERE proposal_id = :prop_id
            ORDER BY extracted_politician_name, extracted_parliamentary_group_name
        """)

        result = await self.session.execute(query, {"prop_id": proposal_id})
        rows = result.fetchall()

        return [self._to_entity(row) for row in rows]

    async def get_extraction_summary(
        self, proposal_id: int | None = None
    ) -> dict[str, int]:
        """Get summary statistics for extracted judges."""
        where_clause = ""
        params: dict[str, Any] = {}

        if proposal_id is not None:
            where_clause = "WHERE proposal_id = :prop_id"
            params["prop_id"] = proposal_id

        query = text(f"""
            SELECT matching_status, COUNT(*) as count
            FROM extracted_proposal_judges
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
            "needs_review": 0,
        }

        for row in rows:
            status = row.matching_status
            count = getattr(row, "count", 0)  # Use getattr to access the count
            if status in summary:
                summary[status] = count
            summary["total"] += count

        return summary

    async def bulk_create(
        self, judges: list[ExtractedProposalJudge]
    ) -> list[ExtractedProposalJudge]:
        """Create multiple extracted judges at once."""
        if not judges:
            return []

        # Build values for bulk insert
        values = []
        for judge in judges:
            value_dict: dict[str, Any] = {
                "proposal_id": judge.proposal_id,
                "extracted_politician_name": judge.extracted_politician_name,
                "extracted_party_name": judge.extracted_party_name,
                "extracted_parliamentary_group_name": (
                    judge.extracted_parliamentary_group_name
                ),
                "extracted_judgment": judge.extracted_judgment,
                "source_url": judge.source_url,
                "extracted_at": judge.extracted_at,
                "matching_status": judge.matching_status,
            }

            # Add optional fields if present
            if judge.matched_politician_id:
                value_dict["matched_politician_id"] = judge.matched_politician_id
            if judge.matched_parliamentary_group_id:
                value_dict["matched_parliamentary_group_id"] = (
                    judge.matched_parliamentary_group_id
                )
            if judge.matching_confidence is not None:
                value_dict["matching_confidence"] = judge.matching_confidence
            if judge.matched_at:
                value_dict["matched_at"] = judge.matched_at
            if hasattr(judge, "additional_data") and judge.additional_data:
                value_dict["additional_data"] = judge.additional_data

            values.append(value_dict)

        # Create bulk insert query
        query = text("""
            INSERT INTO extracted_proposal_judges (
                proposal_id, extracted_politician_name, extracted_party_name,
                extracted_parliamentary_group_name, extracted_judgment, source_url,
                extracted_at, matched_politician_id, matched_parliamentary_group_id,
                matching_confidence, matching_status, matched_at, additional_data
            )
            VALUES (
                :proposal_id, :extracted_politician_name, :extracted_party_name,
                :extracted_parliamentary_group_name, :extracted_judgment, :source_url,
                :extracted_at, :matched_politician_id, :matched_parliamentary_group_id,
                :matching_confidence, :matching_status, :matched_at, :additional_data
            )
            RETURNING id, proposal_id, extracted_politician_name,
                      extracted_party_name, extracted_parliamentary_group_name,
                      extracted_judgment, source_url, extracted_at,
                      matched_politician_id, matched_parliamentary_group_id,
                      matching_confidence, matching_status, matched_at,
                      additional_data
        """)

        created_judges = []
        for value in values:
            # Set defaults for optional fields
            value.setdefault("matched_politician_id", None)
            value.setdefault("matched_parliamentary_group_id", None)
            value.setdefault("matching_confidence", None)
            value.setdefault("matched_at", None)
            value.setdefault("additional_data", None)

            result = await self.session.execute(query, value)
            row = result.fetchone()
            if row:
                created_judges.append(self._to_entity(row))

        await self.session.commit()
        return created_judges

    async def convert_to_proposal_judge(
        self, extracted_judge: ExtractedProposalJudge
    ) -> ProposalJudge:
        """Convert an extracted judge to a ProposalJudge entity."""
        if not extracted_judge.is_matched():
            raise ValueError(
                f"Cannot convert unmatched extracted judge "
                f"(status: {extracted_judge.matching_status})"
            )

        params = extracted_judge.convert_to_proposal_judge_params()
        return ProposalJudge(**params)

    async def bulk_convert_to_proposal_judges(
        self, proposal_id: int | None = None
    ) -> list[ProposalJudge]:
        """Convert all matched judges for a proposal to ProposalJudge entities."""
        matched_judges = await self.get_matched_judges(proposal_id=proposal_id)
        result = []

        for judge in matched_judges:
            try:
                proposal_judge = await self.convert_to_proposal_judge(judge)
                result.append(proposal_judge)
            except ValueError:
                # Skip judges that cannot be converted
                continue

        return result

    def _to_entity(self, model: Any) -> ExtractedProposalJudge:
        """Convert database model to domain entity."""
        return ExtractedProposalJudge(
            id=model.id,
            proposal_id=model.proposal_id,
            extracted_politician_name=model.extracted_politician_name,
            extracted_party_name=model.extracted_party_name,
            extracted_parliamentary_group_name=model.extracted_parliamentary_group_name,
            extracted_judgment=model.extracted_judgment,
            source_url=model.source_url,
            extracted_at=model.extracted_at,
            matched_politician_id=model.matched_politician_id,
            matched_parliamentary_group_id=model.matched_parliamentary_group_id,
            matching_confidence=model.matching_confidence,
            matching_status=model.matching_status,
            matched_at=model.matched_at,
            additional_data=getattr(model, "additional_data", None),
        )

    def _to_model(self, entity: ExtractedProposalJudge) -> ExtractedProposalJudgeModel:
        """Convert domain entity to database model."""
        data = {
            "proposal_id": entity.proposal_id,
            "extracted_politician_name": entity.extracted_politician_name,
            "extracted_party_name": entity.extracted_party_name,
            "extracted_parliamentary_group_name": (
                entity.extracted_parliamentary_group_name
            ),
            "extracted_judgment": entity.extracted_judgment,
            "source_url": entity.source_url,
            "extracted_at": entity.extracted_at,
            "matched_politician_id": entity.matched_politician_id,
            "matched_parliamentary_group_id": entity.matched_parliamentary_group_id,
            "matching_confidence": entity.matching_confidence,
            "matching_status": entity.matching_status,
            "matched_at": entity.matched_at,
        }

        if hasattr(entity, "additional_data") and entity.additional_data is not None:
            data["additional_data"] = entity.additional_data
        if entity.id is not None:
            data["id"] = entity.id

        return ExtractedProposalJudgeModel(**data)

    def _update_model(
        self,
        model: ExtractedProposalJudgeModel,
        entity: ExtractedProposalJudge,
    ) -> None:
        """Update model fields from entity."""
        model.proposal_id = entity.proposal_id
        model.extracted_politician_name = entity.extracted_politician_name
        model.extracted_party_name = entity.extracted_party_name
        model.extracted_parliamentary_group_name = (
            entity.extracted_parliamentary_group_name
        )
        model.extracted_judgment = entity.extracted_judgment
        model.source_url = entity.source_url
        model.extracted_at = entity.extracted_at
        model.matched_politician_id = entity.matched_politician_id
        model.matched_parliamentary_group_id = entity.matched_parliamentary_group_id
        model.matching_confidence = entity.matching_confidence
        model.matching_status = entity.matching_status
        model.matched_at = entity.matched_at

        if hasattr(entity, "additional_data") and entity.additional_data is not None:
            model.additional_data = entity.additional_data

    async def get_pending_by_proposal(
        self, proposal_id: int
    ) -> list[ExtractedProposalJudge]:
        """Get pending judges for a specific proposal."""
        return await self.get_pending_judges(proposal_id)

    async def get_all_pending(self) -> list[ExtractedProposalJudge]:
        """Get all pending judges."""
        return await self.get_pending_judges()

    async def get_matched_by_proposal(
        self, proposal_id: int
    ) -> list[ExtractedProposalJudge]:
        """Get matched judges for a specific proposal."""
        return await self.get_matched_judges(proposal_id)

    async def get_all_matched(self) -> list[ExtractedProposalJudge]:
        """Get all matched judges."""
        return await self.get_matched_judges()

    async def mark_processed(self, judge_id: int) -> None:
        """Mark a judge as processed."""
        query = text("""
            UPDATE extracted_proposal_judges
            SET matching_status = 'processed',
                matched_at = CURRENT_TIMESTAMP
            WHERE id = :judge_id
        """)
        await self.session.execute(query, {"judge_id": judge_id})

    async def count(self) -> int:
        """Count total number of extracted proposal judges."""
        query = text("SELECT COUNT(*) FROM extracted_proposal_judges")
        result = await self.session.execute(query)
        count = result.scalar()
        return count if count is not None else 0
