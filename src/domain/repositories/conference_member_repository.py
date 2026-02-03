"""Repository interface for conference members."""

from abc import abstractmethod
from datetime import date

from src.domain.entities.conference_member import ConferenceMember
from src.domain.repositories.base import BaseRepository


class ConferenceMemberRepository(BaseRepository[ConferenceMember]):
    """Repository interface for conference members."""

    @abstractmethod
    async def get_by_politician_and_conference(
        self, politician_id: int, conference_id: int, active_only: bool = True
    ) -> list[ConferenceMember]:
        """Get members by politician and conference."""
        pass

    @abstractmethod
    async def get_by_conference(
        self, conference_id: int, active_only: bool = True
    ) -> list[ConferenceMember]:
        """Get all members for a conference."""
        pass

    @abstractmethod
    async def get_by_politician(
        self, politician_id: int, active_only: bool = True
    ) -> list[ConferenceMember]:
        """Get all memberships for a politician."""
        pass

    @abstractmethod
    async def upsert(
        self,
        politician_id: int,
        conference_id: int,
        start_date: date,
        end_date: date | None = None,
        role: str | None = None,
    ) -> ConferenceMember:
        """Create or update a membership."""
        pass

    @abstractmethod
    async def end_membership(
        self, membership_id: int, end_date: date
    ) -> ConferenceMember | None:
        """End a membership by setting the end date."""
        pass

    @abstractmethod
    async def get_by_source_extracted_member_ids(
        self, member_ids: list[int]
    ) -> list[ConferenceMember]:
        """source_extracted_member_idのリストから所属情報を一括取得する."""
        pass
