"""Parliamentary group repository interface."""

from abc import abstractmethod

from src.domain.entities.parliamentary_group import ParliamentaryGroup
from src.domain.repositories.base import BaseRepository


class ParliamentaryGroupRepository(BaseRepository[ParliamentaryGroup]):
    """Repository interface for parliamentary groups."""

    @abstractmethod
    async def get_by_name_and_governing_body(
        self, name: str, governing_body_id: int
    ) -> ParliamentaryGroup | None:
        """Get parliamentary group by name and governing body."""
        pass

    @abstractmethod
    async def get_by_governing_body_id(
        self, governing_body_id: int, active_only: bool = True
    ) -> list[ParliamentaryGroup]:
        """Get all parliamentary groups for a governing body."""
        pass

    @abstractmethod
    async def get_active(self) -> list[ParliamentaryGroup]:
        """Get all active parliamentary groups."""
        pass
