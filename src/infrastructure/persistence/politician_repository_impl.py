"""Politician repository implementation (async-only)."""

import logging

from typing import Any

from sqlalchemy import text
from sqlalchemy.exc import IntegrityError as SQLIntegrityError
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.ext.asyncio import AsyncSession

from src.domain.entities.politician import Politician
from src.domain.repositories.politician_repository import PoliticianRepository
from src.domain.repositories.session_adapter import ISessionAdapter
from src.infrastructure.persistence.base_repository_impl import BaseRepositoryImpl


logger = logging.getLogger(__name__)


class PoliticianModel:
    """Politician database model (dynamic)."""

    def __init__(self, **kwargs: Any):
        for key, value in kwargs.items():
            setattr(self, key, value)


class PoliticianRepositoryImpl(BaseRepositoryImpl[Politician], PoliticianRepository):
    """Async-only implementation of politician repository using SQLAlchemy."""

    def __init__(
        self,
        session: AsyncSession | ISessionAdapter,
        model_class: type[Any] | None = None,
    ):
        """Initialize repository.

        Args:
            session: AsyncSession or ISessionAdapter for database operations
            model_class: Optional model class for compatibility
        """
        # Use dynamic model if no model class provided
        if model_class is None:
            model_class = PoliticianModel

        super().__init__(session, Politician, model_class)

    @property
    def _table_name(self) -> str:
        return "politicians"

    async def get_by_name(self, name: str) -> Politician | None:
        """Get politician by name."""
        query = text("""
            SELECT * FROM politicians
            WHERE name = :name
            LIMIT 1
        """)
        result = await self.session.execute(query, {"name": name})
        row = result.fetchone()
        return self._row_to_entity(row) if row else None

    async def search_by_name(self, name_pattern: str) -> list[Politician]:
        """Search politicians by name pattern."""
        query = text("""
            SELECT * FROM politicians
            WHERE name ILIKE :pattern
            ORDER BY name
        """)
        result = await self.session.execute(query, {"pattern": f"%{name_pattern}%"})
        rows = result.fetchall()
        return [self._row_to_entity(row) for row in rows]

    async def upsert(self, politician: Politician) -> Politician:
        """Insert or update politician (upsert)."""
        # Check if exists
        existing = await self.get_by_name(politician.name)

        if existing:
            # Update existing
            politician.id = existing.id
            return await self.update(politician)
        else:
            # Create new using base class create (which commits)
            return await self.create(politician)

    async def bulk_create_politicians(
        self, politicians_data: list[dict[str, Any]]
    ) -> dict[str, list[Politician] | list[dict[str, Any]]]:
        """Bulk create or update politicians.

        Returns dict for backward compatibility with legacy code.
        """
        created: list[Politician] = []
        updated: list[Politician] = []
        errors: list[dict[str, Any]] = []

        for data in politicians_data:
            try:
                # Check existing politician
                existing = await self.get_by_name(
                    data.get("name", ""),
                )

                if existing:
                    # Update if needed
                    needs_update = False
                    # 外部データキー→エンティティ属性名のマッピング
                    field_mapping = {
                        "prefecture": "prefecture",
                        "electoral_district": "district",
                        "profile_url": "profile_page_url",
                        "party_position": "party_position",
                    }
                    for data_key, entity_attr in field_mapping.items():
                        if data_key in data and data[data_key] != getattr(
                            existing, entity_attr, None
                        ):
                            setattr(existing, entity_attr, data[data_key])
                            needs_update = True

                    if needs_update:
                        updated_politician = await self.update(existing)
                        updated.append(updated_politician)
                else:
                    # Create new politician
                    new_politician = Politician(
                        name=data.get("name", ""),
                        prefecture=data.get("prefecture", ""),
                        district=data.get("electoral_district", ""),
                        profile_page_url=data.get("profile_url"),
                    )
                    created_politician = await self.create_entity(new_politician)
                    created.append(created_politician)

            except SQLIntegrityError as e:
                logger.error(
                    f"Integrity error processing politician {data.get('name')}: {e}"
                )
                errors.append(
                    {
                        "data": data,
                        "error": f"Duplicate or constraint violation: {str(e)}",
                    }
                )
            except SQLAlchemyError as e:
                logger.error(
                    f"Database error processing politician {data.get('name')}: {e}"
                )
                errors.append({"data": data, "error": f"Database error: {str(e)}"})
            except Exception as e:
                logger.error(
                    f"Unexpected error processing politician {data.get('name')}: {e}"
                )
                errors.append({"data": data, "error": f"Unexpected error: {str(e)}"})

        # Commit changes
        await self.session.commit()

        return {"created": created, "updated": updated, "errors": errors}

    async def fetch_as_dict_async(
        self, query: str, params: dict[str, Any] | None = None
    ) -> list[dict[str, Any]]:
        """Execute raw SQL query and return results as dictionaries (async)."""
        result = await self.session.execute(text(query), params or {})
        rows = result.fetchall()
        return [dict(row._mapping) for row in rows]  # type: ignore[attr-defined]

    async def create_entity(self, entity: Politician) -> Politician:
        """Create a new politician entity (async) without committing."""
        # Create without committing (for bulk operations)
        model = self._to_model(entity)

        self.session.add(model)
        # Don't commit here - let the caller decide when to commit
        await self.session.flush()  # Flush to get the ID without committing
        await self.session.refresh(model)

        return self._to_entity(model)

    async def get_all(
        self, limit: int | None = None, offset: int | None = 0
    ) -> list[Politician]:
        """Get all politicians."""
        query_text = """
            SELECT p.*
            FROM politicians p
            ORDER BY p.name
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

    async def get_by_id(self, entity_id: int) -> Politician | None:
        """Get politician by ID."""
        query = text("""
            SELECT p.*
            FROM politicians p
            WHERE p.id = :id
        """)

        result = await self.session.execute(query, {"id": entity_id})
        row = result.fetchone()

        if row:
            return self._row_to_entity(row)
        return None

    async def get_by_ids(self, entity_ids: list[int]) -> list[Politician]:
        """Get politicians by their IDs."""
        if not entity_ids:
            return []
        placeholders = ", ".join(f":id_{i}" for i in range(len(entity_ids)))
        query = text(f"""
            SELECT p.*
            FROM politicians p
            WHERE p.id IN ({placeholders})
        """)
        params = {f"id_{i}": eid for i, eid in enumerate(entity_ids)}
        result = await self.session.execute(query, params)
        return [self._row_to_entity(row) for row in result.fetchall()]

    async def create(self, entity: Politician) -> Politician:
        """Create a new politician."""
        query = text("""
            INSERT INTO politicians (
                name, prefecture,
                district, profile_page_url, furigana
            )
            VALUES (
                :name, :prefecture,
                :district, :profile_page_url, :furigana
            )
            RETURNING *
        """)

        params = {
            "name": entity.name,
            "prefecture": entity.prefecture,
            "district": entity.district,
            "profile_page_url": entity.profile_page_url,
            "furigana": entity.furigana,
        }

        result = await self.session.execute(query, params)
        await self.session.commit()

        row = result.first()
        if row:
            return self._row_to_entity(row)
        raise RuntimeError("Failed to create politician")

    async def update(self, entity: Politician) -> Politician:
        """Update an existing politician."""
        from src.infrastructure.exceptions import UpdateError

        query = text("""
            UPDATE politicians
            SET name = :name,
                prefecture = :prefecture,
                district = :district,
                profile_page_url = :profile_page_url,
                furigana = :furigana
            WHERE id = :id
            RETURNING *
        """)

        params = {
            "id": entity.id,
            "name": entity.name,
            "prefecture": entity.prefecture,
            "district": entity.district,
            "profile_page_url": entity.profile_page_url,
            "furigana": entity.furigana,
        }

        result = await self.session.execute(query, params)
        await self.session.commit()

        row = result.first()
        if row:
            return self._row_to_entity(row)
        raise UpdateError(f"Politician with ID {entity.id} not found")

    async def delete(self, entity_id: int) -> bool:
        """Delete a politician by ID."""
        query = text("DELETE FROM politicians WHERE id = :id")

        result = await self.session.execute(query, {"id": entity_id})
        await self.session.commit()

        return result.rowcount > 0  # type: ignore[attr-defined]

    async def count(self) -> int:
        """Count total number of politicians."""
        query = text("SELECT COUNT(*) FROM politicians")
        result = await self.session.execute(query)
        count = result.scalar()
        return count if count is not None else 0

    def _row_to_entity(self, row: Any) -> Politician:
        """Convert database row to domain entity."""
        if row is None:
            raise ValueError("Cannot convert None to Politician entity")

        # Handle both Row and dict objects
        if hasattr(row, "_mapping"):
            data = dict(row._mapping)  # type: ignore[attr-defined]
        elif isinstance(row, dict):
            data = row
        else:
            # Try to access as attributes
            data = {
                "id": getattr(row, "id", None),
                "name": getattr(row, "name", None),
                "prefecture": getattr(row, "prefecture", None),
                "district": getattr(row, "district", None),
                "profile_page_url": getattr(row, "profile_page_url", None),
                "party_position": getattr(row, "party_position", None),
                "furigana": getattr(row, "furigana", None),
            }

        return Politician(
            name=str(data.get("name") or ""),
            prefecture=str(data.get("prefecture") or ""),
            district=str(data.get("district") or ""),
            furigana=data.get("furigana"),
            profile_page_url=data.get("profile_page_url"),
            party_position=data.get("party_position"),
            id=data.get("id"),
        )

    def _to_entity(self, model: Any) -> Politician:
        """Convert database model to domain entity."""
        return self._row_to_entity(model)

    def _to_model(self, entity: Politician) -> Any:
        """Convert domain entity to database model."""
        return self.model_class(
            name=entity.name,
            prefecture=entity.prefecture,
            district=entity.district,
            profile_page_url=entity.profile_page_url,
            party_position=entity.party_position,
            furigana=entity.furigana,
            id=entity.id,
        )

    def _update_model(self, model: Any, entity: Politician) -> None:
        """Update model fields from entity."""
        model.name = entity.name
        model.prefecture = entity.prefecture
        model.district = entity.district
        model.profile_page_url = entity.profile_page_url
        model.furigana = entity.furigana

    async def search_by_normalized_name(self, normalized_name: str) -> list[Politician]:
        """空白除去した名前で政治家を検索する."""
        query = text("""
            SELECT * FROM politicians
            WHERE REPLACE(REPLACE(name, ' ', ''), '　', '') = :name
        """)
        result = await self.session.execute(query, {"name": normalized_name})
        rows = result.fetchall()
        return [self._row_to_entity(row) for row in rows]

    async def get_all_for_matching(self) -> list[dict[str, Any]]:
        """Get all politicians for matching purposes.

        政党名はparty_membership_history経由で取得する。
        """
        query = text("""
            SELECT p.id, p.name, p.furigana, p.party_position, p.district,
                   pp.name as party_name
            FROM politicians p
            LEFT JOIN party_membership_history pmh
                ON p.id = pmh.politician_id AND pmh.end_date IS NULL
            LEFT JOIN political_parties pp ON pmh.political_party_id = pp.id
            ORDER BY p.name
        """)
        result = await self.session.execute(query)
        rows = result.fetchall()

        return [
            {
                "id": row.id,
                "name": row.name,
                "furigana": row.furigana,
                "party_position": row.party_position,
                "district": row.district,
                "party_name": row.party_name,
            }
            for row in rows
        ]

    async def get_related_data_counts(self, politician_id: int) -> dict[str, int]:
        """指定された政治家に紐づく関連データの件数を取得する."""
        counts: dict[str, int] = {}

        # 各テーブルの件数を取得
        tables_with_politician_id = [
            ("speakers", "politician_id"),
            ("parliamentary_group_memberships", "politician_id"),
            ("pledges", "politician_id"),
            ("party_membership_history", "politician_id"),
            ("proposal_judges", "politician_id"),
            ("conference_members", "politician_id"),
        ]

        tables_with_matched_politician_id = [
            ("extracted_parliamentary_group_members", "matched_politician_id"),
            ("extracted_proposal_judges", "matched_politician_id"),
        ]

        for table, column in (
            tables_with_politician_id + tables_with_matched_politician_id
        ):
            query = text(
                f"SELECT COUNT(*) FROM {table} WHERE {column} = :politician_id"
            )
            result = await self.session.execute(query, {"politician_id": politician_id})
            count = result.scalar()
            counts[table] = count if count is not None else 0

        return counts

    async def delete_related_data(self, politician_id: int) -> dict[str, int]:
        """指定された政治家に紐づく関連データを削除・解除する."""
        results: dict[str, int] = {}

        # NULLableカラム: politician_idをNULLに設定
        nullable_tables = [
            ("speakers", "politician_id"),
            ("extracted_parliamentary_group_members", "matched_politician_id"),
            ("extracted_proposal_judges", "matched_politician_id"),
        ]

        for table, column in nullable_tables:
            query = text(
                f"UPDATE {table} SET {column} = NULL WHERE {column} = :politician_id"
            )
            result = await self.session.execute(query, {"politician_id": politician_id})
            results[table] = result.rowcount  # type: ignore[attr-defined]

        # NOT NULLカラム: レコードを削除
        not_null_tables = [
            "parliamentary_group_memberships",
            "pledges",
            "party_membership_history",
            "proposal_judges",
            "conference_members",
        ]

        for table in not_null_tables:
            query = text(f"DELETE FROM {table} WHERE politician_id = :politician_id")
            result = await self.session.execute(query, {"politician_id": politician_id})
            results[table] = result.rowcount  # type: ignore[attr-defined]

        return results
