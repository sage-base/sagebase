"""Meeting repository implementation using SQLAlchemy ORM."""

import json
import logging

from datetime import date
from typing import Any

from sqlalchemy import text, update
from sqlalchemy.ext.asyncio import AsyncSession

from src.domain.entities.meeting import Meeting
from src.domain.repositories.meeting_repository import MeetingRepository
from src.domain.repositories.session_adapter import ISessionAdapter
from src.infrastructure.persistence.base_repository_impl import BaseRepositoryImpl
from src.infrastructure.persistence.sqlalchemy_models import MeetingModel


logger = logging.getLogger(__name__)


class MeetingRepositoryImpl(BaseRepositoryImpl[Meeting], MeetingRepository):
    """Meeting repository implementation using SQLAlchemy ORM.

    async-onlyの実装。sync session対応は削除済み。
    """

    def __init__(self, session: AsyncSession | ISessionAdapter):
        """Initialize repository."""
        super().__init__(session, Meeting, MeetingModel)

    async def get_by_conference_and_date(
        self, conference_id: int, meeting_date: date
    ) -> Meeting | None:
        """Get meeting by conference and date."""
        sql = text(
            "SELECT * FROM meetings WHERE conference_id = :conference_id "
            "AND date = :date LIMIT 1"
        )
        result = await self.session.execute(
            sql, {"conference_id": conference_id, "date": meeting_date}
        )
        row = result.first()
        if row:
            return self._to_entity(row)
        return None

    async def get_by_conference(
        self, conference_id: int, limit: int | None = None
    ) -> list[Meeting]:
        """Get all meetings for a conference."""
        sql = (
            "SELECT * FROM meetings "
            "WHERE conference_id = :conference_id ORDER BY date DESC"
        )
        params: dict[str, Any] = {"conference_id": conference_id}
        if limit:
            sql += " LIMIT :limit"
            params["limit"] = limit
        result = await self.session.execute(text(sql), params)
        return [self._to_entity(row) for row in result.fetchall()]

    async def get_unprocessed(self, limit: int | None = None) -> list[Meeting]:
        """Get meetings that haven't been processed yet."""
        sql = """
            SELECT m.* FROM meetings m
            LEFT JOIN minutes min ON m.id = min.meeting_id
            WHERE min.id IS NULL
            ORDER BY m.date DESC
        """
        if limit:
            sql += f" LIMIT {limit}"
        result = await self.session.execute(text(sql))
        return [self._to_entity(row) for row in result.fetchall()]

    async def update_gcs_uris(
        self,
        meeting_id: int,
        pdf_uri: str | None = None,
        text_uri: str | None = None,
    ) -> bool:
        """Update GCS URIs for a meeting."""
        update_data: dict[str, Any] = {}
        if pdf_uri is not None:
            update_data["gcs_pdf_uri"] = pdf_uri
        if text_uri is not None:
            update_data["gcs_text_uri"] = text_uri

        if not update_data:
            return False

        stmt = (
            update(MeetingModel)
            .where(MeetingModel.id == meeting_id)
            .values(**update_data)
        )
        result = await self.session.execute(stmt)
        await self.session.commit()
        return result.rowcount > 0

    async def update_meeting_gcs_uris(
        self,
        meeting_id: int,
        pdf_uri: str | None = None,
        text_uri: str | None = None,
    ) -> bool:
        """Update GCS URIs for a meeting (backward compatibility alias)."""
        return await self.update_gcs_uris(meeting_id, pdf_uri, text_uri)

    async def get_meetings_with_filters(
        self,
        conference_id: int | None = None,
        governing_body_id: int | None = None,
        offset: int = 0,
        limit: int = 10,
    ) -> tuple[list[dict[str, Any]], int]:
        """Get meetings with filters and pagination."""
        base_query = """
        SELECT
            m.id,
            m.conference_id,
            m.date,
            m.url,
            m.name,
            m.gcs_pdf_uri,
            m.gcs_text_uri,
            m.created_at,
            m.updated_at,
            c.name AS conference_name,
            gb.name AS governing_body_name,
            gb.type AS governing_body_type
        FROM meetings m
        JOIN conferences c ON m.conference_id = c.id
        JOIN governing_bodies gb ON c.governing_body_id = gb.id
        WHERE 1=1
        """

        count_query = """
        SELECT COUNT(*)
        FROM meetings m
        JOIN conferences c ON m.conference_id = c.id
        JOIN governing_bodies gb ON c.governing_body_id = gb.id
        WHERE 1=1
        """

        params: dict[str, Any] = {}

        if conference_id:
            base_query += " AND m.conference_id = :conference_id"
            count_query += " AND m.conference_id = :conference_id"
            params["conference_id"] = conference_id

        if governing_body_id:
            base_query += " AND gb.id = :governing_body_id"
            count_query += " AND gb.id = :governing_body_id"
            params["governing_body_id"] = governing_body_id

        base_query += " ORDER BY m.date DESC, m.id DESC"
        base_query += " LIMIT :limit OFFSET :offset"
        params["limit"] = limit
        params["offset"] = offset

        result = await self.session.execute(text(base_query), params)
        meetings = [dict(row._mapping) for row in result]  # type: ignore

        count_result = await self.session.execute(text(count_query), params)
        total_count = count_result.scalar() or 0

        return meetings, total_count

    async def get_meeting_by_id_with_info(
        self, meeting_id: int
    ) -> dict[str, Any] | None:
        """Get meeting by ID with conference and governing body info."""
        query = text("""
        SELECT
            m.id,
            m.conference_id,
            m.date,
            m.url,
            m.name,
            m.gcs_pdf_uri,
            m.gcs_text_uri,
            m.created_at,
            m.updated_at,
            c.name AS conference_name,
            gb.name AS governing_body_name,
            gb.type AS governing_body_type
        FROM meetings m
        JOIN conferences c ON m.conference_id = c.id
        JOIN governing_bodies gb ON c.governing_body_id = gb.id
        WHERE m.id = :meeting_id
        """)

        result = await self.session.execute(query, {"meeting_id": meeting_id})
        row = result.first()
        return dict(row._mapping) if row else None  # type: ignore

    async def get_by_url(self, url: str) -> Meeting | None:
        """Get meeting by URL."""
        query = text("SELECT * FROM meetings WHERE url = :url LIMIT 1")
        result = await self.session.execute(query, {"url": url})
        row = result.first()
        if row:
            return self._to_entity(row)
        return None

    async def get_by_chamber_and_date_range(
        self, chamber: str, date_from: date, date_to: date
    ) -> list[Meeting]:
        """院名と日付範囲で会議を取得する."""
        sql = text(
            "SELECT m.* FROM meetings m "
            "JOIN conferences c ON m.conference_id = c.id "
            "WHERE c.name LIKE :chamber_prefix "
            "AND m.date BETWEEN :date_from AND :date_to "
            "ORDER BY m.date ASC"
        )
        params = {
            "chamber_prefix": f"{chamber}%",
            "date_from": date_from,
            "date_to": date_to,
        }
        result = await self.session.execute(sql, params)
        return [self._to_entity(row) for row in result.fetchall()]

    async def create(self, entity: Meeting) -> Meeting:
        """Create a new meeting."""
        from datetime import datetime

        sql = text("""
        INSERT INTO meetings (
            conference_id, date, url, name,
            gcs_pdf_uri, gcs_text_uri, attendees_mapping, created_at, updated_at
        )
        VALUES (
            :conference_id, :date, :url, :name,
            :gcs_pdf_uri, :gcs_text_uri, :attendees_mapping,
            :created_at, :updated_at
        )
        RETURNING *
        """)
        params = {
            "conference_id": entity.conference_id,
            "date": entity.date or date.today(),
            "url": entity.url or "",
            "name": entity.name,
            "gcs_pdf_uri": entity.gcs_pdf_uri,
            "gcs_text_uri": entity.gcs_text_uri,
            "attendees_mapping": json.dumps(entity.attendees_mapping)
            if entity.attendees_mapping
            else None,
            "created_at": datetime.now(),
            "updated_at": datetime.now(),
        }
        result = await self.session.execute(sql, params)
        await self.session.flush()
        row = result.first()
        if row:
            return self._to_entity(row)
        raise RuntimeError("Failed to create meeting")

    async def update(self, entity: Meeting) -> Meeting:
        """Update a meeting."""
        from datetime import datetime

        sql = text("""
        UPDATE meetings
        SET conference_id = :conference_id,
            date = :date,
            url = :url,
            name = :name,
            gcs_pdf_uri = :gcs_pdf_uri,
            gcs_text_uri = :gcs_text_uri,
            attendees_mapping = :attendees_mapping,
            updated_at = :updated_at
        WHERE id = :id
        RETURNING *
        """)
        params = {
            "id": entity.id,
            "conference_id": entity.conference_id,
            "date": entity.date,
            "url": entity.url,
            "name": entity.name,
            "gcs_pdf_uri": entity.gcs_pdf_uri,
            "gcs_text_uri": entity.gcs_text_uri,
            "attendees_mapping": json.dumps(entity.attendees_mapping)
            if entity.attendees_mapping
            else None,
            "updated_at": datetime.now(),
        }
        result = await self.session.execute(sql, params)
        await self.session.flush()
        row = result.first()
        if row:
            return self._to_entity(row)
        raise RuntimeError("Failed to update meeting")

    async def delete(self, entity_id: int) -> bool:
        """Delete a meeting."""
        check_sql = text("SELECT COUNT(*) FROM minutes WHERE meeting_id = :meeting_id")
        result = await self.session.execute(check_sql, {"meeting_id": entity_id})
        count = result.scalar()
        if count and count > 0:
            return False

        sql = text("DELETE FROM meetings WHERE id = :id")
        result = await self.session.execute(sql, {"id": entity_id})
        await self.session.flush()
        return getattr(result, "rowcount", 0) > 0  # type: ignore

    async def get_all(
        self, limit: int | None = None, offset: int | None = 0
    ) -> list[Meeting]:
        """Get all meetings."""
        sql = "SELECT * FROM meetings ORDER BY date DESC"
        params: dict[str, Any] = {}
        if limit:
            sql += " LIMIT :limit"
            params["limit"] = limit
        if offset:
            sql += " OFFSET :offset"
            params["offset"] = offset
        result = await self.session.execute(text(sql), params if params else None)
        return [self._to_entity(row) for row in result.fetchall()]

    def _to_entity(self, model: Any) -> Meeting:
        """Convert database model or row to domain entity."""
        if model is None:
            raise ValueError("Cannot convert None to Meeting entity")
        # Row objectの場合は_mappingからdictに変換して読み取り
        if hasattr(model, "_mapping"):
            data = dict(model._mapping)
            return Meeting(
                id=data.get("id"),
                conference_id=data.get("conference_id") or 0,
                date=data.get("date"),
                url=data.get("url"),
                name=data.get("name"),
                gcs_pdf_uri=data.get("gcs_pdf_uri"),
                gcs_text_uri=data.get("gcs_text_uri"),
                attendees_mapping=data.get("attendees_mapping"),
            )
        # ORM model の場合は属性アクセス
        return Meeting(
            id=getattr(model, "id", None),
            conference_id=model.conference_id,
            date=getattr(model, "date", None),
            url=getattr(model, "url", None),
            name=getattr(model, "name", None),
            gcs_pdf_uri=getattr(model, "gcs_pdf_uri", None),
            gcs_text_uri=getattr(model, "gcs_text_uri", None),
            attendees_mapping=getattr(model, "attendees_mapping", None),
        )

    def _to_model(self, entity: Meeting) -> MeetingModel:
        """Convert domain entity to database model."""
        data: dict[str, Any] = {
            "conference_id": entity.conference_id,
            "date": entity.date,
            "url": entity.url,
            "name": entity.name,
            "gcs_pdf_uri": entity.gcs_pdf_uri,
            "gcs_text_uri": entity.gcs_text_uri,
            "attendees_mapping": entity.attendees_mapping,
        }
        if entity.id is not None:
            data["id"] = entity.id
        return MeetingModel(**data)

    def _update_model(self, model: Any, entity: Meeting) -> None:
        """Update database model from domain entity."""
        model.conference_id = entity.conference_id
        model.date = entity.date
        model.url = entity.url
        model.name = entity.name
        model.gcs_pdf_uri = entity.gcs_pdf_uri
        model.gcs_text_uri = entity.gcs_text_uri
        model.attendees_mapping = entity.attendees_mapping
