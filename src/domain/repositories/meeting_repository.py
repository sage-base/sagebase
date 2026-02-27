"""Meeting repository interface."""

from abc import abstractmethod
from datetime import date
from typing import Any

from src.domain.entities.meeting import Meeting
from src.domain.repositories.base import BaseRepository


class MeetingRepository(BaseRepository[Meeting]):
    """Repository interface for meetings."""

    @abstractmethod
    async def get_by_conference_and_date(
        self, conference_id: int, meeting_date: date
    ) -> Meeting | None:
        """Get meeting by conference and date."""
        pass

    @abstractmethod
    async def get_by_conference(
        self, conference_id: int, limit: int | None = None
    ) -> list[Meeting]:
        """Get all meetings for a conference."""
        pass

    @abstractmethod
    async def get_unprocessed(self, limit: int | None = None) -> list[Meeting]:
        """Get meetings that haven't been processed yet."""
        pass

    @abstractmethod
    async def update_gcs_uris(
        self,
        meeting_id: int,
        pdf_uri: str | None = None,
        text_uri: str | None = None,
    ) -> bool:
        """Update GCS URIs for a meeting."""
        pass

    @abstractmethod
    async def get_meetings_with_filters(
        self,
        conference_id: int | None = None,
        governing_body_id: int | None = None,
        offset: int = 0,
        limit: int = 10,
    ) -> tuple[list[dict[str, Any]], int]:
        """Get meetings with filters and pagination.

        Returns:
            Tuple of (meetings list, total count)
        """
        pass

    @abstractmethod
    async def get_meeting_by_id_with_info(
        self, meeting_id: int
    ) -> dict[str, Any] | None:
        """Get meeting by ID with conference and governing body info."""
        pass

    @abstractmethod
    async def get_by_url(self, url: str) -> Meeting | None:
        """Get meeting by URL."""
        pass

    @abstractmethod
    async def get_by_chamber_and_date_range(
        self, chamber: str, date_from: date, date_to: date
    ) -> list[Meeting]:
        """院名と日付範囲で会議を取得する."""
        pass
