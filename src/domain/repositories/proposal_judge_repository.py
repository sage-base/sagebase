"""ProposalJudge repository interface."""

from abc import abstractmethod

from src.domain.entities.proposal_judge import ProposalJudge
from src.domain.repositories.base import BaseRepository


class ProposalJudgeRepository(BaseRepository[ProposalJudge]):
    """ProposalJudge repository interface."""

    @abstractmethod
    async def get_by_proposal(self, proposal_id: int) -> list[ProposalJudge]:
        """Get all judges for a proposal.

        Args:
            proposal_id: ID of the proposal

        Returns:
            List of proposal judges for the specified proposal
        """
        pass

    @abstractmethod
    async def get_by_politician(self, politician_id: int) -> list[ProposalJudge]:
        """Get all proposal judges by a politician.

        Args:
            politician_id: ID of the politician

        Returns:
            List of proposal judges by the specified politician
        """
        pass

    @abstractmethod
    async def get_by_proposal_and_politician(
        self, proposal_id: int, politician_id: int
    ) -> ProposalJudge | None:
        """Get a specific judge by proposal and politician.

        Args:
            proposal_id: ID of the proposal
            politician_id: ID of the politician

        Returns:
            The proposal judge if found, None otherwise
        """
        pass

    @abstractmethod
    async def bulk_create(self, judges: list[ProposalJudge]) -> list[ProposalJudge]:
        """Create multiple proposal judges at once.

        Args:
            judges: List of ProposalJudge entities to create

        Returns:
            List of created ProposalJudge entities with IDs
        """
        pass

    @abstractmethod
    async def get_by_source_group_judge_id(
        self, source_group_judge_id: int
    ) -> list[ProposalJudge]:
        """Get all judges created from a specific group judge.

        Args:
            source_group_judge_id: ID of the source ProposalParliamentaryGroupJudge

        Returns:
            List of proposal judges created from the specified group judge
        """
        pass

    @abstractmethod
    async def bulk_update(self, judges: list[ProposalJudge]) -> list[ProposalJudge]:
        """Update multiple proposal judges at once.

        Args:
            judges: List of ProposalJudge entities to update

        Returns:
            List of updated ProposalJudge entities
        """
        pass
