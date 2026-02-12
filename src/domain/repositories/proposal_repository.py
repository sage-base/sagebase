"""Proposal repository interface."""

from abc import abstractmethod

from src.domain.entities.proposal import Proposal
from src.domain.repositories.base import BaseRepository


class ProposalRepository(BaseRepository[Proposal]):
    """Proposal repository interface."""

    @abstractmethod
    async def get_by_meeting_id(self, meeting_id: int) -> list[Proposal]:
        """Get proposals by meeting ID.

        Args:
            meeting_id: Meeting ID to filter by

        Returns:
            List of proposals associated with the specified meeting
        """
        pass

    @abstractmethod
    async def get_by_conference_id(self, conference_id: int) -> list[Proposal]:
        """Get proposals by conference ID.

        Args:
            conference_id: Conference ID to filter by

        Returns:
            List of proposals associated with the specified conference
        """
        pass

    @abstractmethod
    async def get_filtered_paginated(
        self,
        *,
        meeting_id: int | None = None,
        conference_id: int | None = None,
        session_number: int | None = None,
        deliberation_status: str | None = None,
        limit: int = 20,
        offset: int = 0,
    ) -> list[Proposal]:
        """フィルター条件付きでページネーションされた議案を取得する.

        Args:
            meeting_id: 会議IDフィルター（指定時のみ適用）
            conference_id: 会議体IDフィルター（指定時のみ適用）
            session_number: 提出回次フィルター（指定時のみ適用）
            deliberation_status: 審議状況フィルター（指定時のみ適用）
            limit: 取得件数
            offset: スキップ件数

        Returns:
            議案リスト
        """
        pass

    @abstractmethod
    async def count_filtered(
        self,
        *,
        meeting_id: int | None = None,
        conference_id: int | None = None,
        session_number: int | None = None,
        deliberation_status: str | None = None,
    ) -> int:
        """フィルター条件付きで議案件数を取得する.

        Args:
            meeting_id: 会議IDフィルター（指定時のみ適用）
            conference_id: 会議体IDフィルター（指定時のみ適用）
            session_number: 提出回次フィルター（指定時のみ適用）
            deliberation_status: 審議状況フィルター（指定時のみ適用）

        Returns:
            議案件数
        """
        pass

    @abstractmethod
    async def find_by_url(self, url: str) -> Proposal | None:
        """Find proposal by URL.

        Args:
            url: URL of the proposal (detail_url, status_url, or votes_url)

        Returns:
            Proposal if found, None otherwise
        """
        pass

    @abstractmethod
    async def find_by_identifier(
        self,
        governing_body_id: int,
        session_number: int,
        proposal_number: int,
        proposal_type: str,
    ) -> Proposal | None:
        """Find proposal by unique identifier combination.

        Args:
            governing_body_id: Governing body ID
            session_number: Session number
            proposal_number: Proposal number
            proposal_type: Proposal type

        Returns:
            Proposal if found, None otherwise
        """
        pass

    @abstractmethod
    async def bulk_create(self, entities: list[Proposal]) -> list[Proposal]:
        """Create multiple proposals at once.

        Args:
            entities: List of Proposal entities to create

        Returns:
            List of created Proposal entities with IDs
        """
        pass

    @abstractmethod
    async def get_distinct_deliberation_statuses(self) -> list[str]:
        """審議状況のユニーク値一覧を取得する.

        Returns:
            審議状況の文字列リスト（NULL除外、ソート済み）
        """
        pass
