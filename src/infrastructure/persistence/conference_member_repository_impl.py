"""ConferenceMember repository implementation using SQLAlchemy."""

from datetime import date
from typing import Any

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from src.domain.entities.conference_member import ConferenceMember
from src.domain.repositories.conference_member_repository import (
    ConferenceMemberRepository as IConferenceMemberRepository,
)
from src.domain.repositories.session_adapter import ISessionAdapter
from src.infrastructure.persistence.base_repository_impl import BaseRepositoryImpl


class ConferenceMemberModel:
    """Conference member database model (dynamic)."""

    id: int | None
    politician_id: int
    conference_id: int
    start_date: date
    end_date: date | None
    role: str | None
    is_manually_verified: bool
    latest_extraction_log_id: int | None

    def __init__(self, **kwargs: Any):
        for key, value in kwargs.items():
            setattr(self, key, value)


class ConferenceMemberRepositoryImpl(
    BaseRepositoryImpl[ConferenceMember], IConferenceMemberRepository
):
    """Implementation of ConferenceMemberRepository using SQLAlchemy."""

    def __init__(self, session: AsyncSession | ISessionAdapter):
        super().__init__(session, ConferenceMember, ConferenceMemberModel)

    async def get_by_id(self, entity_id: int) -> ConferenceMember | None:
        """Get a conference member by ID using raw SQL."""
        query = text("""
            SELECT * FROM politician_affiliations
            WHERE id = :id
        """)
        result = await self.session.execute(query, {"id": entity_id})
        row = result.fetchone()
        if row:
            return self._row_to_entity(row)
        return None

    async def create(self, entity: ConferenceMember) -> ConferenceMember:
        """Create a new conference member using raw SQL."""
        query = text("""
            INSERT INTO politician_affiliations (
                politician_id, conference_id, start_date, end_date, role,
                is_manually_verified, latest_extraction_log_id
            ) VALUES (
                :politician_id, :conference_id, :start_date, :end_date, :role,
                :is_manually_verified, :latest_extraction_log_id
            )
            RETURNING *
        """)

        result = await self.session.execute(
            query,
            {
                "politician_id": entity.politician_id,
                "conference_id": entity.conference_id,
                "start_date": entity.start_date,
                "end_date": entity.end_date,
                "role": entity.role,
                "is_manually_verified": entity.is_manually_verified,
                "latest_extraction_log_id": entity.latest_extraction_log_id,
            },
        )
        row = result.fetchone()
        await self.session.commit()
        return self._row_to_entity(row)

    async def delete(self, entity_id: int) -> bool:
        """Delete a conference member by ID using raw SQL."""
        query = text("""
            DELETE FROM politician_affiliations
            WHERE id = :id
        """)
        result = await self.session.execute(query, {"id": entity_id})
        await self.session.commit()
        return result.rowcount > 0

    async def get_by_politician_and_conference(
        self, politician_id: int, conference_id: int, active_only: bool = True
    ) -> list[ConferenceMember]:
        """Get members by politician and conference."""
        conditions = ["politician_id = :pol_id", "conference_id = :conf_id"]
        params: dict[str, Any] = {"pol_id": politician_id, "conf_id": conference_id}

        if active_only:
            conditions.append("end_date IS NULL")

        query = text(f"""
            SELECT * FROM politician_affiliations
            WHERE {" AND ".join(conditions)}
            ORDER BY start_date DESC
        """)

        result = await self.session.execute(query, params)
        rows = result.fetchall()

        return [self._row_to_entity(row) for row in rows]

    async def get_by_conference(
        self, conference_id: int, active_only: bool = True
    ) -> list[ConferenceMember]:
        """Get all members for a conference."""
        conditions = ["conference_id = :conf_id"]
        params: dict[str, Any] = {"conf_id": conference_id}

        if active_only:
            conditions.append("end_date IS NULL")

        query = text(f"""
            SELECT * FROM politician_affiliations
            WHERE {" AND ".join(conditions)}
            ORDER BY start_date DESC
        """)

        result = await self.session.execute(query, params)
        rows = result.fetchall()

        return [self._row_to_entity(row) for row in rows]

    async def get_by_politician(
        self, politician_id: int, active_only: bool = True
    ) -> list[ConferenceMember]:
        """Get all memberships for a politician."""
        conditions = ["politician_id = :pol_id"]
        params: dict[str, Any] = {"pol_id": politician_id}

        if active_only:
            conditions.append("end_date IS NULL")

        query = text(f"""
            SELECT * FROM politician_affiliations
            WHERE {" AND ".join(conditions)}
            ORDER BY start_date DESC
        """)

        result = await self.session.execute(query, params)
        rows = result.fetchall()

        return [self._row_to_entity(row) for row in rows]

    async def get_by_conference_at_date(
        self, conference_id: int, target_date: date
    ) -> list[ConferenceMember]:
        """指定日時点で会議体に所属するメンバーを取得する."""
        query = text("""
            SELECT * FROM politician_affiliations
            WHERE conference_id = :conf_id
              AND start_date <= :target_date
              AND (end_date IS NULL OR end_date >= :target_date)
            ORDER BY start_date DESC
        """)
        result = await self.session.execute(
            query, {"conf_id": conference_id, "target_date": target_date}
        )
        rows = result.fetchall()
        return [self._row_to_entity(row) for row in rows]

    async def upsert(
        self,
        politician_id: int,
        conference_id: int,
        start_date: date,
        end_date: date | None = None,
        role: str | None = None,
    ) -> ConferenceMember:
        """Create or update a membership."""
        # Check if membership already exists
        query = text("""
            SELECT * FROM politician_affiliations
            WHERE politician_id = :pol_id
              AND conference_id = :conf_id
              AND start_date = :start_date
            LIMIT 1
        """)

        result = await self.session.execute(
            query,
            {
                "pol_id": politician_id,
                "conf_id": conference_id,
                "start_date": start_date,
            },
        )
        existing_row = result.fetchone()

        if existing_row:
            # Update existing
            update_stmt = text("""
                UPDATE politician_affiliations
                SET end_date = :end_date, role = :role
                WHERE id = :id
            """)
            await self.session.execute(
                update_stmt, {"id": existing_row.id, "end_date": end_date, "role": role}
            )
            await self.session.commit()
            return self._row_to_entity(existing_row)
        else:
            # Create new
            entity = ConferenceMember(
                politician_id=politician_id,
                conference_id=conference_id,
                start_date=start_date,
                end_date=end_date,
                role=role,
            )
            return await self.create(entity)

    async def end_membership(
        self, membership_id: int, end_date: date
    ) -> ConferenceMember | None:
        """End a membership by setting the end date."""
        query = text("""
            UPDATE politician_affiliations
            SET end_date = :end_date
            WHERE id = :id
        """)

        await self.session.execute(query, {"id": membership_id, "end_date": end_date})
        await self.session.commit()

        # Return updated entity
        return await self.get_by_id(membership_id)

    def _row_to_entity(self, row: Any) -> ConferenceMember:
        """Convert database row to domain entity."""
        return ConferenceMember(
            id=row.id,
            politician_id=row.politician_id,
            conference_id=row.conference_id,
            start_date=row.start_date,
            end_date=row.end_date,
            role=getattr(row, "role", None),
            is_manually_verified=bool(getattr(row, "is_manually_verified", False)),
            latest_extraction_log_id=getattr(row, "latest_extraction_log_id", None),
        )

    def _to_entity(self, model: ConferenceMemberModel) -> ConferenceMember:
        """Convert database model to domain entity."""
        return ConferenceMember(
            id=model.id,
            politician_id=model.politician_id,
            conference_id=model.conference_id,
            start_date=model.start_date,
            end_date=model.end_date,
            role=model.role,
            is_manually_verified=bool(getattr(model, "is_manually_verified", False)),
            latest_extraction_log_id=getattr(model, "latest_extraction_log_id", None),
        )

    def _to_model(self, entity: ConferenceMember) -> ConferenceMemberModel:
        """Convert domain entity to database model."""
        data = {
            "politician_id": entity.politician_id,
            "conference_id": entity.conference_id,
            "start_date": entity.start_date,
            "end_date": entity.end_date,
            "role": entity.role,
            "is_manually_verified": entity.is_manually_verified,
            "latest_extraction_log_id": entity.latest_extraction_log_id,
        }

        if entity.id is not None:
            data["id"] = entity.id

        return ConferenceMemberModel(**data)

    def _update_model(
        self,
        model: ConferenceMemberModel,
        entity: ConferenceMember,
    ) -> None:
        """Update model fields from entity."""
        model.politician_id = entity.politician_id
        model.conference_id = entity.conference_id
        model.start_date = entity.start_date
        model.end_date = entity.end_date
        model.role = entity.role
        model.is_manually_verified = entity.is_manually_verified
        model.latest_extraction_log_id = entity.latest_extraction_log_id
