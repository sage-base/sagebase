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
    async def get_by_conference_at_date(
        self, conference_id: int, target_date: date
    ) -> list[ConferenceMember]:
        """指定日時点で会議体に所属するメンバーを取得する.

        start_date <= target_date かつ (end_date IS NULL または end_date >= target_date)
        の条件で絞り込む。

        Args:
            conference_id: 会議体ID
            target_date: 対象日

        Returns:
            該当するConferenceMemberのリスト
        """
        pass

    @abstractmethod
    async def end_membership(
        self, membership_id: int, end_date: date
    ) -> ConferenceMember | None:
        """End a membership by setting the end date."""
        pass
