"""Politician repository implementation (async-only) using SQLAlchemy ORM."""

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
from src.infrastructure.persistence.sqlalchemy_models import PoliticianModel


logger = logging.getLogger(__name__)


class PoliticianRepositoryImpl(BaseRepositoryImpl[Politician], PoliticianRepository):
    """Async-only implementation of politician repository using SQLAlchemy ORM."""

    # --- 政治家に紐づくリレーションテーブル定義 ---
    # NULLableカラム（削除時はNULL設定、マージ時は付け替え）
    _NULLABLE_FK_TABLES: list[tuple[str, str]] = [
        ("speakers", "politician_id"),
        ("extracted_parliamentary_group_members", "matched_politician_id"),
        ("extracted_proposal_judges", "matched_politician_id"),
    ]

    # NOT NULLカラム + UNIQUE制約あり（マージ時は重複DELETE後にUPDATE）
    # (テーブル名, FKカラム名, UNIQUE制約のパートナーカラム名)
    _UNIQUE_CONSTRAINT_TABLES: list[tuple[str, str, str]] = [
        ("election_members", "politician_id", "election_id"),
        ("proposal_judge_politicians", "politician_id", "judge_id"),
        ("proposal_submitters", "politician_id", "proposal_id"),
    ]

    # NOT NULLカラム + UNIQUE制約なし（削除時はDELETE、マージ時は単純UPDATE）
    _NOT_NULL_FK_TABLES: list[tuple[str, str]] = [
        ("parliamentary_group_memberships", "politician_id"),
        ("party_membership_history", "politician_id"),
        ("conference_members", "politician_id"),
        ("pledges", "politician_id"),
        ("proposal_judges", "politician_id"),
    ]

    # FK制約なし（操作ログ）
    _LOG_TABLE = ("politician_operation_logs", "politician_id")

    def __init__(self, session: AsyncSession | ISessionAdapter):
        """Initialize repository."""
        super().__init__(session, Politician, PoliticianModel)

    async def get_by_name(self, name: str) -> Politician | None:
        """Get politician by name."""
        query = text("""
            SELECT * FROM politicians
            WHERE name = :name
            LIMIT 1
        """)
        result = await self.session.execute(query, {"name": name})
        row = result.fetchone()
        return self._to_entity(row) if row else None

    async def search_by_name(self, name_pattern: str) -> list[Politician]:
        """Search politicians by name pattern."""
        query = text("""
            SELECT * FROM politicians
            WHERE name ILIKE :pattern
            ORDER BY name
        """)
        result = await self.session.execute(query, {"pattern": f"%{name_pattern}%"})
        rows = result.fetchall()
        return [self._to_entity(row) for row in rows]

    async def upsert(self, politician: Politician) -> Politician:
        """Insert or update politician (upsert)."""
        existing = await self.get_by_name(politician.name)

        if existing:
            politician.id = existing.id
            return await self.update(politician)
        else:
            return await self.create(politician)

    async def bulk_create_politicians(
        self, politicians_data: list[dict[str, Any]]
    ) -> dict[str, list[Politician] | list[dict[str, Any]]]:
        """Bulk create or update politicians."""
        created: list[Politician] = []
        updated: list[Politician] = []
        errors: list[dict[str, Any]] = []

        for data in politicians_data:
            try:
                existing = await self.get_by_name(
                    data.get("name", ""),
                )

                if existing:
                    needs_update = False
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
        model = self._to_model(entity)
        self.session.add(model)
        await self.session.flush()
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

        return [self._to_entity(row) for row in rows]

    async def create(self, entity: Politician) -> Politician:
        """Create a new politician."""
        query = text("""
            INSERT INTO politicians (
                name, prefecture,
                district, profile_page_url, furigana,
                is_lastname_hiragana, is_firstname_hiragana, kanji_name
            )
            VALUES (
                :name, :prefecture,
                :district, :profile_page_url, :furigana,
                :is_lastname_hiragana, :is_firstname_hiragana, :kanji_name
            )
            RETURNING *
        """)

        params = {
            "name": entity.name,
            "prefecture": entity.prefecture,
            "district": entity.district,
            "profile_page_url": entity.profile_page_url,
            "furigana": entity.furigana,
            "is_lastname_hiragana": entity.is_lastname_hiragana,
            "is_firstname_hiragana": entity.is_firstname_hiragana,
            "kanji_name": entity.kanji_name,
        }

        result = await self.session.execute(query, params)
        await self.session.commit()

        row = result.first()
        if row:
            return self._to_entity(row)
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
                furigana = :furigana,
                is_lastname_hiragana = :is_lastname_hiragana,
                is_firstname_hiragana = :is_firstname_hiragana,
                kanji_name = :kanji_name
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
            "is_lastname_hiragana": entity.is_lastname_hiragana,
            "is_firstname_hiragana": entity.is_firstname_hiragana,
            "kanji_name": entity.kanji_name,
        }

        result = await self.session.execute(query, params)
        await self.session.commit()

        row = result.first()
        if row:
            return self._to_entity(row)
        raise UpdateError(f"Politician with ID {entity.id} not found")

    async def delete(self, entity_id: int) -> bool:
        """Delete a politician by ID."""
        query = text("DELETE FROM politicians WHERE id = :id")

        result = await self.session.execute(query, {"id": entity_id})
        await self.session.commit()

        return result.rowcount > 0  # type: ignore[attr-defined]

    def _to_entity(self, model: Any) -> Politician:
        """Convert database model or row to domain entity."""
        if model is None:
            raise ValueError("Cannot convert None to Politician entity")
        return Politician(
            name=str(getattr(model, "name", "") or ""),
            prefecture=str(getattr(model, "prefecture", "") or ""),
            district=str(getattr(model, "district", "") or ""),
            furigana=getattr(model, "furigana", None),
            profile_page_url=getattr(model, "profile_page_url", None),
            party_position=getattr(model, "party_position", None),
            id=getattr(model, "id", None),
            is_lastname_hiragana=bool(getattr(model, "is_lastname_hiragana", False)),
            is_firstname_hiragana=bool(getattr(model, "is_firstname_hiragana", False)),
            kanji_name=getattr(model, "kanji_name", None),
        )

    def _to_model(self, entity: Politician) -> PoliticianModel:
        """Convert domain entity to database model."""
        data: dict[str, Any] = {
            "name": entity.name,
            "prefecture": entity.prefecture,
            "district": entity.district,
            "profile_page_url": entity.profile_page_url,
            "furigana": entity.furigana,
            "is_lastname_hiragana": entity.is_lastname_hiragana,
            "is_firstname_hiragana": entity.is_firstname_hiragana,
            "kanji_name": entity.kanji_name,
        }
        if entity.id is not None:
            data["id"] = entity.id
        return PoliticianModel(**data)

    def _update_model(self, model: Any, entity: Politician) -> None:
        """Update model fields from entity."""
        model.name = entity.name
        model.prefecture = entity.prefecture
        model.district = entity.district
        model.profile_page_url = entity.profile_page_url
        model.furigana = entity.furigana
        model.is_lastname_hiragana = entity.is_lastname_hiragana
        model.is_firstname_hiragana = entity.is_firstname_hiragana
        model.kanji_name = entity.kanji_name

    async def search_by_normalized_name(self, normalized_name: str) -> list[Politician]:
        """空白除去した名前で政治家を検索する."""
        query = text("""
            SELECT * FROM politicians
            WHERE REPLACE(REPLACE(name, ' ', ''), '　', '') = :name
        """)
        result = await self.session.execute(query, {"name": normalized_name})
        rows = result.fetchall()
        return [self._to_entity(row) for row in rows]

    async def get_all_for_matching(self) -> list[dict[str, Any]]:
        """Get all politicians for matching purposes."""
        query = text("""
            SELECT p.id, p.name, p.furigana, p.party_position, p.district,
                   p.kanji_name,
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
                "kanji_name": row.kanji_name,
            }
            for row in rows
        ]

    async def get_related_data_counts(self, politician_id: int) -> dict[str, int]:
        """指定された政治家に紐づく関連データの件数を取得する."""
        counts: dict[str, int] = {}

        all_tables = (
            self._NULLABLE_FK_TABLES
            + [(t, col) for t, col, _ in self._UNIQUE_CONSTRAINT_TABLES]
            + self._NOT_NULL_FK_TABLES
        )

        for table, column in all_tables:
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

        for table, column in self._NULLABLE_FK_TABLES:
            query = text(
                f"UPDATE {table} SET {column} = NULL WHERE {column} = :politician_id"
            )
            result = await self.session.execute(query, {"politician_id": politician_id})
            results[table] = result.rowcount  # type: ignore[attr-defined]

        all_not_null = [
            (t, col) for t, col, _ in self._UNIQUE_CONSTRAINT_TABLES
        ] + self._NOT_NULL_FK_TABLES

        for table, column in all_not_null:
            query = text(f"DELETE FROM {table} WHERE {column} = :politician_id")
            result = await self.session.execute(query, {"politician_id": politician_id})
            results[table] = result.rowcount  # type: ignore[attr-defined]

        return results

    async def _reassign_with_dedup(
        self,
        table: str,
        fk_column: str,
        unique_partner_column: str,
        source_id: int,
        target_id: int,
    ) -> int:
        """UNIQUE制約付きテーブルで重複DELETEしてからUPDATEする."""
        delete_dup_query = text(
            f"DELETE FROM {table} "
            f"WHERE {fk_column} = :source_id "
            f"AND {unique_partner_column} IN ("
            f"  SELECT {unique_partner_column} FROM {table} "
            f"  WHERE {fk_column} = :target_id"
            f")"
        )
        dup_result = await self.session.execute(
            delete_dup_query, {"source_id": source_id, "target_id": target_id}
        )
        update_query = text(
            f"UPDATE {table} SET {fk_column} = :target_id "
            f"WHERE {fk_column} = :source_id"
        )
        upd_result = await self.session.execute(
            update_query, {"target_id": target_id, "source_id": source_id}
        )
        return dup_result.rowcount + upd_result.rowcount  # type: ignore[attr-defined]

    async def merge_politicians(self, source_id: int, target_id: int) -> dict[str, int]:
        """統合元の全リレーションを統合先に付け替え、統合元を削除する."""
        results: dict[str, int] = {}

        # --- Nullableカラム: source → target に付け替え ---
        for table, column in self._NULLABLE_FK_TABLES:
            query = text(
                f"UPDATE {table} SET {column} = :target_id WHERE {column} = :source_id"
            )
            result = await self.session.execute(
                query, {"target_id": target_id, "source_id": source_id}
            )
            results[table] = result.rowcount  # type: ignore[attr-defined]

        # --- UNIQUE制約あり: 重複DELETE後にUPDATE ---
        for table, fk_col, unique_col in self._UNIQUE_CONSTRAINT_TABLES:
            results[table] = await self._reassign_with_dedup(
                table, fk_col, unique_col, source_id, target_id
            )

        # --- NOT NULLカラム（UNIQUE制約なし）: 単純にUPDATE ---
        for table, column in self._NOT_NULL_FK_TABLES:
            query = text(
                f"UPDATE {table} SET {column} = :target_id WHERE {column} = :source_id"
            )
            result = await self.session.execute(
                query, {"target_id": target_id, "source_id": source_id}
            )
            results[table] = result.rowcount  # type: ignore[attr-defined]

        # --- 操作ログ ---
        log_table, log_column = self._LOG_TABLE
        query = text(
            f"UPDATE {log_table} SET {log_column} = :target_id "
            f"WHERE {log_column} = :source_id"
        )
        result = await self.session.execute(
            query, {"target_id": target_id, "source_id": source_id}
        )
        results[log_table] = result.rowcount  # type: ignore[attr-defined]

        # --- 統合元の政治家レコードを削除 ---
        delete_query = text("DELETE FROM politicians WHERE id = :source_id")
        await self.session.execute(delete_query, {"source_id": source_id})

        return results
