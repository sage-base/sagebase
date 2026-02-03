"""Repository interface for extracted conference members."""

from abc import abstractmethod

from src.domain.entities.extracted_conference_member import ExtractedConferenceMember
from src.domain.repositories.base import BaseRepository


class ExtractedConferenceMemberRepository(BaseRepository[ExtractedConferenceMember]):
    """Repository interface for extracted conference members.

    Bronze Layer（抽出ログ層）のリポジトリインターフェース。
    政治家との紐付け機能はGold Layer（ConferenceMemberRepository）に移行済み。
    """

    @abstractmethod
    async def get_by_conference(
        self, conference_id: int
    ) -> list[ExtractedConferenceMember]:
        """Get all extracted members for a conference."""
        pass

    @abstractmethod
    async def get_extraction_summary(
        self, conference_id: int | None = None
    ) -> dict[str, int]:
        """Get summary statistics for extracted members.

        Returns:
            dict with 'total' key containing the count of members.
        """
        pass

    @abstractmethod
    async def bulk_create(
        self, members: list[ExtractedConferenceMember]
    ) -> list[ExtractedConferenceMember]:
        """Create multiple extracted members at once."""
        pass
