"""ParliamentaryGroup repository implementation using SQLAlchemy."""

from typing import Any

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from .parliamentary_group_membership_repository_impl import (
    ParliamentaryGroupMembershipRepositoryImpl,
)

from src.domain.entities.parliamentary_group import ParliamentaryGroup
from src.domain.repositories.parliamentary_group_repository import (
    ParliamentaryGroupRepository as IParliamentaryGroupRepository,
)
from src.domain.repositories.session_adapter import ISessionAdapter
from src.infrastructure.persistence.base_repository_impl import BaseRepositoryImpl


class ParliamentaryGroupModel:
    """Parliamentary group database model (dynamic)."""

    id: int | None
    name: str
    governing_body_id: int
    url: str | None
    description: str | None
    is_active: bool
    political_party_id: int | None
    chamber: str

    def __init__(self, **kwargs: Any):
        for key, value in kwargs.items():
            setattr(self, key, value)


class ParliamentaryGroupRepositoryImpl(
    BaseRepositoryImpl[ParliamentaryGroup], IParliamentaryGroupRepository
):
    """Implementation of ParliamentaryGroupRepository using SQLAlchemy."""

    def __init__(self, session: AsyncSession | ISessionAdapter):
        super().__init__(session, ParliamentaryGroup, ParliamentaryGroupModel)

    async def create(self, entity: ParliamentaryGroup) -> ParliamentaryGroup:
        """Create a new parliamentary group using raw SQL."""
        query = text(
            """
            INSERT INTO parliamentary_groups (
                name, governing_body_id, url, description,
                is_active, political_party_id, chamber
            )
            VALUES (
                :name, :governing_body_id, :url, :description,
                :is_active, :political_party_id, :chamber
            )
            RETURNING id, name, governing_body_id, url,
                description, is_active, political_party_id, chamber
        """
        )

        result = await self.session.execute(
            query,
            {
                "name": entity.name,
                "governing_body_id": entity.governing_body_id,
                "url": entity.url,
                "description": entity.description,
                "is_active": entity.is_active,
                "political_party_id": entity.political_party_id,
                "chamber": entity.chamber,
            },
        )
        row = result.fetchone()

        if row:
            return self._row_to_entity(row)
        raise ValueError("Failed to create parliamentary group")

    async def update(self, entity: ParliamentaryGroup) -> ParliamentaryGroup:
        """Update an existing parliamentary group using raw SQL."""
        if not entity.id:
            raise ValueError("Entity must have an ID to update")

        query = text("""
            UPDATE parliamentary_groups
            SET name = :name,
                governing_body_id = :governing_body_id,
                url = :url,
                description = :description,
                is_active = :is_active,
                political_party_id = :political_party_id,
                chamber = :chamber
            WHERE id = :id
            RETURNING id, name, governing_body_id, url,
                description, is_active, political_party_id, chamber
        """)

        result = await self.session.execute(
            query,
            {
                "id": entity.id,
                "name": entity.name,
                "governing_body_id": entity.governing_body_id,
                "url": entity.url,
                "description": entity.description,
                "is_active": entity.is_active,
                "political_party_id": entity.political_party_id,
                "chamber": entity.chamber,
            },
        )
        row = result.fetchone()

        if row:
            return self._row_to_entity(row)
        raise ValueError(f"Parliamentary group with ID {entity.id} not found")

    async def get_by_name_and_governing_body(
        self, name: str, governing_body_id: int, chamber: str = ""
    ) -> ParliamentaryGroup | None:
        """Get parliamentary group by name and governing body."""
        query = text("""
            SELECT * FROM parliamentary_groups
            WHERE name = :name AND governing_body_id = :gb_id
                AND chamber = :chamber
            LIMIT 1
        """)

        result = await self.session.execute(
            query, {"name": name, "gb_id": governing_body_id, "chamber": chamber}
        )
        row = result.fetchone()

        if row:
            return self._row_to_entity(row)
        return None

    async def get_by_governing_body_id(
        self,
        governing_body_id: int,
        active_only: bool = True,
        chamber: str | None = None,
    ) -> list[ParliamentaryGroup]:
        """Get all parliamentary groups for a governing body."""
        conditions = ["governing_body_id = :gb_id"]
        params: dict[str, Any] = {"gb_id": governing_body_id}

        if active_only:
            conditions.append("is_active = TRUE")

        if chamber is not None:
            conditions.append("chamber = :chamber")
            params["chamber"] = chamber

        query = text(f"""
            SELECT * FROM parliamentary_groups
            WHERE {" AND ".join(conditions)}
            ORDER BY name
        """)

        result = await self.session.execute(query, params)
        rows = result.fetchall()

        return [self._row_to_entity(row) for row in rows]

    async def get_active(self) -> list[ParliamentaryGroup]:
        """Get all active parliamentary groups."""
        query = text("""
            SELECT * FROM parliamentary_groups
            WHERE is_active = TRUE
            ORDER BY name
        """)

        result = await self.session.execute(query)
        rows = result.fetchall()

        return [self._row_to_entity(row) for row in rows]

    async def get_all(
        self, limit: int | None = None, offset: int | None = 0
    ) -> list[ParliamentaryGroup]:
        """Get all parliamentary groups."""
        query_text = """
            SELECT pg.*, gb.name as governing_body_name
            FROM parliamentary_groups pg
            JOIN governing_bodies gb ON pg.governing_body_id = gb.id
            ORDER BY gb.name, pg.name
        """
        params = {}

        if limit is not None:
            query_text += " LIMIT :limit OFFSET :offset"
            params = {"limit": limit, "offset": offset or 0}

        result = await self.session.execute(
            text(query_text), params if params else None
        )
        rows = result.fetchall()

        return [self._row_to_entity(row) for row in rows]

    async def get_all_with_details(
        self,
        governing_body_id: int | None = None,
        active_only: bool = True,
        with_url_only: bool = False,
    ) -> list[dict[str, Any]]:
        """
        Get all parliamentary groups with governing body details.

        Returns dictionary format for CLI display purposes.

        Args:
            governing_body_id: Filter to specific governing body (optional)
            active_only: Filter to only active groups
            with_url_only: Filter to only groups with URL set

        Returns:
            List of dictionaries with parliamentary group details
        """
        query_text = """
            SELECT pg.*, gb.name as governing_body_name
            FROM parliamentary_groups pg
            JOIN governing_bodies gb ON pg.governing_body_id = gb.id
            WHERE 1=1
        """
        params: dict[str, Any] = {}

        if governing_body_id is not None:
            query_text += " AND pg.governing_body_id = :governing_body_id"
            params["governing_body_id"] = governing_body_id

        if active_only:
            query_text += " AND pg.is_active = true"

        if with_url_only:
            query_text += " AND pg.url IS NOT NULL"

        query_text += " ORDER BY gb.id, pg.name"

        result = await self.session.execute(text(query_text), params or None)
        rows = result.fetchall()

        # Convert rows to dictionaries
        if rows:
            keys = result.keys()
            return [dict(zip(keys, row, strict=False)) for row in rows]
        return []

    async def get_by_id(self, entity_id: int) -> ParliamentaryGroup | None:
        """Get parliamentary group by ID."""
        query = text("SELECT * FROM parliamentary_groups WHERE id = :id")
        result = await self.session.execute(query, {"id": entity_id})
        row = result.fetchone()

        if row:
            return self._row_to_entity(row)
        return None

    async def get_by_ids(self, entity_ids: list[int]) -> list[ParliamentaryGroup]:
        """Get parliamentary groups by their IDs."""
        if not entity_ids:
            return []
        placeholders = ", ".join(f":id_{i}" for i in range(len(entity_ids)))
        query = text(f"""
            SELECT * FROM parliamentary_groups
            WHERE id IN ({placeholders})
        """)
        params = {f"id_{i}": eid for i, eid in enumerate(entity_ids)}
        result = await self.session.execute(query, params)
        return [self._row_to_entity(row) for row in result.fetchall()]

    def _row_to_entity(self, row: Any) -> ParliamentaryGroup:
        """Convert database row to domain entity."""
        return ParliamentaryGroup(
            id=row.id,
            name=row.name,
            governing_body_id=row.governing_body_id,
            url=getattr(row, "url", None),
            description=getattr(row, "description", None),
            is_active=getattr(row, "is_active", True),
            political_party_id=getattr(row, "political_party_id", None),
            chamber=getattr(row, "chamber", ""),
        )

    def _to_entity(self, model: ParliamentaryGroupModel) -> ParliamentaryGroup:
        """Convert database model to domain entity."""
        return ParliamentaryGroup(
            id=model.id,
            name=model.name,
            governing_body_id=model.governing_body_id,
            url=getattr(model, "url", None),
            description=model.description,
            is_active=model.is_active,
            political_party_id=getattr(model, "political_party_id", None),
            chamber=getattr(model, "chamber", ""),
        )

    def _to_model(self, entity: ParliamentaryGroup) -> ParliamentaryGroupModel:
        """Convert domain entity to database model."""
        data: dict[str, Any] = {
            "name": entity.name,
            "governing_body_id": entity.governing_body_id,
            "description": entity.description,
            "is_active": entity.is_active,
            "political_party_id": entity.political_party_id,
            "chamber": entity.chamber,
        }

        if entity.url is not None:
            data["url"] = entity.url
        if entity.id is not None:
            data["id"] = entity.id

        return ParliamentaryGroupModel(**data)

    def _update_model(
        self, model: ParliamentaryGroupModel, entity: ParliamentaryGroup
    ) -> None:
        """Update model fields from entity."""
        model.name = entity.name
        model.governing_body_id = entity.governing_body_id
        model.description = entity.description
        model.is_active = entity.is_active
        model.political_party_id = entity.political_party_id
        model.chamber = entity.chamber

        if entity.url is not None:
            model.url = entity.url


__all__ = [
    "ParliamentaryGroupRepositoryImpl",
    "ParliamentaryGroupMembershipRepositoryImpl",
]
