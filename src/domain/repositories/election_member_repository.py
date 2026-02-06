"""選挙結果メンバーリポジトリのインターフェース."""

from abc import abstractmethod

from src.domain.entities.election_member import ElectionMember
from src.domain.repositories.base import BaseRepository


class ElectionMemberRepository(BaseRepository[ElectionMember]):
    """Repository interface for election members."""

    @abstractmethod
    async def get_by_election_id(self, election_id: int) -> list[ElectionMember]:
        """選挙IDに属する全メンバーを取得.

        Args:
            election_id: 選挙ID

        Returns:
            選挙結果メンバーエンティティのリスト
        """
        pass

    @abstractmethod
    async def get_by_politician_id(self, politician_id: int) -> list[ElectionMember]:
        """政治家IDに紐づく全選挙結果を取得.

        Args:
            politician_id: 政治家ID

        Returns:
            選挙結果メンバーエンティティのリスト
        """
        pass
