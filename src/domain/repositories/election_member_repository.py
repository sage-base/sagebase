"""選挙結果メンバーリポジトリのインターフェース."""

from abc import abstractmethod

from src.domain.entities.election_member import ElectionMember
from src.domain.repositories.base import BaseRepository


class ElectionMemberRepository(BaseRepository[ElectionMember]):
    """選挙結果メンバーのリポジトリインターフェース."""

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

    @abstractmethod
    async def delete_by_election_id(self, election_id: int) -> int:
        """選挙IDに属する全メンバーを削除.

        Args:
            election_id: 選挙ID

        Returns:
            削除件数
        """
        pass

    @abstractmethod
    async def delete_by_election_id_and_results(
        self, election_id: int, results: list[str]
    ) -> int:
        """選挙IDおよび結果値に一致するメンバーを削除.

        Args:
            election_id: 選挙ID
            results: 削除対象の結果値リスト（例: ["比例当選", "比例復活"]）

        Returns:
            削除件数
        """
        pass
