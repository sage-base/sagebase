"""GoverningBody repository implementation using SQLAlchemy."""

from typing import Any

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from src.domain.entities.governing_body import GoverningBody
from src.domain.repositories.governing_body_repository import (
    GoverningBodyRepository as IGoverningBodyRepository,
)
from src.domain.repositories.session_adapter import ISessionAdapter
from src.infrastructure.persistence.base_repository_impl import BaseRepositoryImpl


class GoverningBodyModel:
    """Governing body database model (dynamic)."""

    id: int | None
    name: str
    type: str | None
    organization_code: str | None
    organization_type: str | None

    def __init__(self, **kwargs: Any):
        for key, value in kwargs.items():
            setattr(self, key, value)


class GoverningBodyRepositoryImpl(
    BaseRepositoryImpl[GoverningBody], IGoverningBodyRepository
):
    """Implementation of GoverningBodyRepository using SQLAlchemy."""

    def __init__(self, session: AsyncSession | ISessionAdapter):
        super().__init__(session, GoverningBody, GoverningBodyModel)

    async def get_all(
        self, limit: int | None = None, offset: int | None = None
    ) -> list[GoverningBody]:
        """Get all governing bodies with conference count."""
        query = text("""
            SELECT gb.*,
                   COUNT(c.id) as conference_count
            FROM governing_bodies gb
            LEFT JOIN conferences c ON gb.id = c.governing_body_id
            GROUP BY gb.id, gb.name, gb.type, gb.organization_code, gb.organization_type
            ORDER BY gb.name
        """)

        if limit:
            query = text(str(query) + " LIMIT :limit")
        if offset:
            query = text(str(query) + " OFFSET :offset")

        params = {}
        if limit:
            params["limit"] = limit
        if offset:
            params["offset"] = offset

        result = await self.session.execute(query, params if params else None)
        rows = result.fetchall()

        return [self._row_to_entity(row) for row in rows]

    async def get_by_id(self, entity_id: int) -> GoverningBody | None:
        """Get governing body by ID with conference count."""
        query = text("""
            SELECT gb.*,
                   COUNT(c.id) as conference_count
            FROM governing_bodies gb
            LEFT JOIN conferences c ON gb.id = c.governing_body_id
            WHERE gb.id = :id
            GROUP BY gb.id, gb.name, gb.type, gb.organization_code, gb.organization_type
        """)

        result = await self.session.execute(query, {"id": entity_id})
        row = result.fetchone()

        if row:
            return self._row_to_entity(row)
        return None

    async def get_by_ids(self, entity_ids: list[int]) -> list[GoverningBody]:
        """Get governing bodies by their IDs."""
        if not entity_ids:
            return []
        placeholders = ", ".join(f":id_{i}" for i in range(len(entity_ids)))
        query = text(f"""
            SELECT gb.*,
                   COUNT(c.id) as conference_count
            FROM governing_bodies gb
            LEFT JOIN conferences c ON gb.id = c.governing_body_id
            WHERE gb.id IN ({placeholders})
            GROUP BY gb.id, gb.name, gb.type, gb.organization_code, gb.organization_type
        """)
        params = {f"id_{i}": eid for i, eid in enumerate(entity_ids)}
        result = await self.session.execute(query, params)
        return [self._row_to_entity(row) for row in result.fetchall()]

    async def get_by_name_and_type(
        self, name: str, type: str | None = None
    ) -> GoverningBody | None:
        """Get governing body by name and type."""
        conditions = ["name = :name"]
        params: dict[str, Any] = {"name": name}

        if type is not None:
            conditions.append("type = :type")
            params["type"] = type

        query = text(f"""
            SELECT * FROM governing_bodies
            WHERE {" AND ".join(conditions)}
            LIMIT 1
        """)

        result = await self.session.execute(query, params)
        row = result.fetchone()

        if row:
            return self._row_to_entity(row)
        return None

    async def get_by_organization_code(
        self, organization_code: str
    ) -> GoverningBody | None:
        """Get governing body by organization code."""
        query = text("""
            SELECT * FROM governing_bodies
            WHERE organization_code = :org_code
            LIMIT 1
        """)

        result = await self.session.execute(query, {"org_code": organization_code})
        row = result.fetchone()

        if row:
            return self._row_to_entity(row)
        return None

    async def search_by_name(self, name_pattern: str) -> list[GoverningBody]:
        """Search governing bodies by name pattern."""
        query = text("""
            SELECT * FROM governing_bodies
            WHERE name ILIKE :pattern
            ORDER BY name
        """)

        result = await self.session.execute(query, {"pattern": f"%{name_pattern}%"})
        rows = result.fetchall()

        return [self._row_to_entity(row) for row in rows]

    async def count_with_conferences(self) -> int:
        """Count governing bodies that have at least one conference."""
        query = text("""
            SELECT COUNT(DISTINCT governing_body_id)
            FROM conferences
        """)

        result = await self.session.execute(query)
        count = result.scalar()
        return count if count is not None else 0

    async def count_with_meetings(self) -> int:
        """Count governing bodies that have at least one meeting."""
        query = text("""
            SELECT COUNT(DISTINCT c.governing_body_id)
            FROM meetings m
            JOIN conferences c ON m.conference_id = c.id
        """)

        result = await self.session.execute(query)
        count = result.scalar()
        return count if count is not None else 0

    async def count(self) -> int:
        """Count total number of governing bodies."""
        query = text("SELECT COUNT(*) FROM governing_bodies")
        result = await self.session.execute(query)
        count = result.scalar()
        return count if count is not None else 0

    def _row_to_entity(self, row: Any) -> GoverningBody:
        """Convert database row to domain entity."""
        return GoverningBody(
            id=row.id,
            name=row.name,
            type=row.type,
            organization_code=getattr(row, "organization_code", None),
            organization_type=getattr(row, "organization_type", None),
            conference_count=getattr(row, "conference_count", 0),
        )

    def _to_entity(self, model: GoverningBodyModel) -> GoverningBody:
        """Convert database model to domain entity."""
        return GoverningBody(
            id=model.id,
            name=model.name,
            type=model.type,
            organization_code=getattr(model, "organization_code", None),
            organization_type=getattr(model, "organization_type", None),
            conference_count=getattr(model, "conference_count", 0),
        )

    def _to_model(self, entity: GoverningBody) -> GoverningBodyModel:
        """Convert domain entity to database model."""
        data = {
            "name": entity.name,
            "type": entity.type,
        }

        if entity.organization_code is not None:
            data["organization_code"] = entity.organization_code
        if entity.organization_type is not None:
            data["organization_type"] = entity.organization_type
        if entity.id is not None:
            data["id"] = entity.id

        return GoverningBodyModel(**data)

    def _update_model(self, model: GoverningBodyModel, entity: GoverningBody) -> None:
        """Update model fields from entity."""
        model.name = entity.name
        model.type = entity.type

        if entity.organization_code is not None:
            model.organization_code = entity.organization_code
        if entity.organization_type is not None:
            model.organization_type = entity.organization_type

    async def create(self, entity: GoverningBody) -> GoverningBody:
        """Create a new governing body.

        Args:
            entity: GoverningBody entity to create

        Returns:
            Created GoverningBody entity with ID
        """
        query = text("""
            INSERT INTO governing_bodies (
                name, type, organization_code, organization_type
            )
            VALUES (
                :name, :type, :organization_code, :organization_type
            )
            RETURNING *
        """)

        params = {
            "name": entity.name,
            "type": entity.type,
            "organization_code": entity.organization_code,
            "organization_type": entity.organization_type,
        }

        result = await self.session.execute(query, params)
        await self.session.commit()

        row = result.first()
        if row:
            return self._row_to_entity(row)
        raise RuntimeError("Failed to create governing body")

    async def update(self, entity: GoverningBody) -> GoverningBody:
        """Update an existing governing body.

        Args:
            entity: GoverningBody entity to update

        Returns:
            Updated GoverningBody entity
        """
        from src.infrastructure.exceptions import UpdateError

        query = text("""
            UPDATE governing_bodies
            SET name = :name,
                type = :type,
                organization_code = :organization_code,
                organization_type = :organization_type
            WHERE id = :id
            RETURNING *
        """)

        params = {
            "id": entity.id,
            "name": entity.name,
            "type": entity.type,
            "organization_code": entity.organization_code,
            "organization_type": entity.organization_type,
        }

        result = await self.session.execute(query, params)
        await self.session.commit()

        row = result.first()
        if row:
            return self._row_to_entity(row)
        raise UpdateError(f"GoverningBody with ID {entity.id} not found")

    async def delete(self, entity_id: int) -> bool:
        """Delete a governing body by ID.

        Args:
            entity_id: GoverningBody ID to delete

        Returns:
            True if deleted, False otherwise
        """
        # Check if there are related conferences
        check_query = text("""
            SELECT COUNT(*) FROM conferences
            WHERE governing_body_id = :governing_body_id
        """)
        result = await self.session.execute(
            check_query, {"governing_body_id": entity_id}
        )
        count = result.scalar()

        if count and count > 0:
            return False  # Cannot delete if there are related conferences

        query = text("DELETE FROM governing_bodies WHERE id = :id")
        result = await self.session.execute(query, {"id": entity_id})
        await self.session.commit()

        return result.rowcount > 0  # type: ignore[attr-defined]
