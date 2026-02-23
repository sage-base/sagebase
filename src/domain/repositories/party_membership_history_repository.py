"""政党所属履歴リポジトリインターフェース."""

from abc import abstractmethod
from datetime import date

from src.domain.entities.party_membership_history import PartyMembershipHistory
from src.domain.repositories.base import BaseRepository


class PartyMembershipHistoryRepository(BaseRepository[PartyMembershipHistory]):
    """政党所属履歴のリポジトリインターフェース."""

    @abstractmethod
    async def get_by_politician(
        self, politician_id: int
    ) -> list[PartyMembershipHistory]:
        """政治家IDで所属履歴を取得する（start_date降順）.

        Args:
            politician_id: 政治家ID

        Returns:
            所属履歴リスト
        """
        pass

    @abstractmethod
    async def get_by_political_party(
        self, political_party_id: int
    ) -> list[PartyMembershipHistory]:
        """政党IDで所属履歴を取得する.

        Args:
            political_party_id: 政党ID

        Returns:
            所属履歴リスト
        """
        pass

    @abstractmethod
    async def get_current_by_politician(
        self, politician_id: int, as_of_date: date | None = None
    ) -> PartyMembershipHistory | None:
        """政治家の現在の所属を取得する.

        Args:
            politician_id: 政治家ID
            as_of_date: 基準日（Noneの場合は今日）

        Returns:
            現在の所属履歴、なければNone
        """
        pass

    @abstractmethod
    async def get_current_by_politicians(
        self, politician_ids: list[int], as_of_date: date | None = None
    ) -> dict[int, PartyMembershipHistory]:
        """複数政治家の指定日時点の所属を一括取得する.

        Args:
            politician_ids: 政治家IDリスト
            as_of_date: 基準日（Noneの場合は今日）

        Returns:
            politician_id → 現在の所属履歴のマッピング
        """
        pass

    @abstractmethod
    async def end_membership(
        self, membership_id: int, end_date: date
    ) -> PartyMembershipHistory | None:
        """所属を終了する.

        Args:
            membership_id: 所属履歴ID
            end_date: 終了日

        Returns:
            更新された所属履歴、見つからない場合はNone
        """
        pass
