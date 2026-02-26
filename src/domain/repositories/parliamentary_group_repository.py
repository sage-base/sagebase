"""Parliamentary group repository interface."""

from abc import abstractmethod
from datetime import date

from src.domain.entities.parliamentary_group import ParliamentaryGroup
from src.domain.repositories.base import BaseRepository


class ParliamentaryGroupRepository(BaseRepository[ParliamentaryGroup]):
    """Repository interface for parliamentary groups."""

    @abstractmethod
    async def get_by_name_and_governing_body(
        self, name: str, governing_body_id: int, chamber: str = ""
    ) -> ParliamentaryGroup | None:
        """Get parliamentary group by name and governing body."""
        pass

    @abstractmethod
    async def get_by_governing_body_id(
        self,
        governing_body_id: int,
        active_only: bool = True,
        chamber: str | None = None,
        as_of_date: date | None = None,
    ) -> list[ParliamentaryGroup]:
        """Get all parliamentary groups for a governing body.

        Args:
            governing_body_id: 開催主体ID
            active_only: Trueの場合、is_active=Trueの会派のみ返す
            chamber: 院の指定（衆議院/参議院）
            as_of_date: 指定日時点で有効な会派のみ返す（active_onlyより優先）
        """
        pass

    @abstractmethod
    async def get_active(self) -> list[ParliamentaryGroup]:
        """Get all active parliamentary groups."""
        pass
