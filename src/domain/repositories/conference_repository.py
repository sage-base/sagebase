"""Conference repository interface."""

from abc import abstractmethod

from src.domain.entities.conference import Conference
from src.domain.repositories.base import BaseRepository


class ConferenceRepository(BaseRepository[Conference]):
    """Repository interface for conferences."""

    @abstractmethod
    async def get_by_name_and_governing_body(
        self, name: str, governing_body_id: int, term: str | None = None
    ) -> Conference | None:
        """Get conference by name, governing body, and optionally term."""
        pass

    @abstractmethod
    async def get_by_governing_body(self, governing_body_id: int) -> list[Conference]:
        """Get all conferences for a governing body."""
        pass
