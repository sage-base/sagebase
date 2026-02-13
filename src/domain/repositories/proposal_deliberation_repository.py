"""ProposalDeliberation repository interface."""

from abc import abstractmethod

from src.domain.entities.proposal_deliberation import ProposalDeliberation
from src.domain.repositories.base import BaseRepository


class ProposalDeliberationRepository(BaseRepository[ProposalDeliberation]):
    """ProposalDeliberation repository interface."""

    @abstractmethod
    async def get_by_proposal_id(self, proposal_id: int) -> list[ProposalDeliberation]:
        pass

    @abstractmethod
    async def get_by_conference_id(
        self, conference_id: int
    ) -> list[ProposalDeliberation]:
        pass

    @abstractmethod
    async def get_by_meeting_id(self, meeting_id: int) -> list[ProposalDeliberation]:
        pass

    @abstractmethod
    async def find_by_proposal_and_conference(
        self,
        proposal_id: int,
        conference_id: int,
        meeting_id: int | None = None,
        stage: str | None = None,
    ) -> ProposalDeliberation | None:
        pass
