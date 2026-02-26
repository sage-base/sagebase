"""会派⇔政党の多対多関連リポジトリインターフェース."""

from abc import abstractmethod

from src.domain.entities.parliamentary_group_party import ParliamentaryGroupParty
from src.domain.repositories.base import BaseRepository


class ParliamentaryGroupPartyRepository(BaseRepository[ParliamentaryGroupParty]):
    """会派と政党の多対多関連を管理するリポジトリインターフェース."""

    @abstractmethod
    async def get_by_parliamentary_group_id(
        self, group_id: int
    ) -> list[ParliamentaryGroupParty]:
        """会派IDで関連政党を取得する.

        Args:
            group_id: 会派ID

        Returns:
            該当会派に紐づく関連エンティティのリスト
        """
        pass

    @abstractmethod
    async def get_by_political_party_id(
        self, party_id: int
    ) -> list[ParliamentaryGroupParty]:
        """政党IDで関連会派を取得する.

        Args:
            party_id: 政党ID

        Returns:
            該当政党に紐づく関連エンティティのリスト
        """
        pass

    @abstractmethod
    async def get_primary_party(self, group_id: int) -> ParliamentaryGroupParty | None:
        """会派の主要政党を取得する.

        Args:
            group_id: 会派ID

        Returns:
            is_primary=trueの関連エンティティ、存在しない場合はNone
        """
        pass

    @abstractmethod
    async def add_party(
        self, group_id: int, party_id: int, is_primary: bool = False
    ) -> ParliamentaryGroupParty:
        """会派に政党を追加する.

        Args:
            group_id: 会派ID
            party_id: 政党ID
            is_primary: 主要政党フラグ

        Returns:
            作成された関連エンティティ
        """
        pass

    @abstractmethod
    async def remove_party(self, group_id: int, party_id: int) -> bool:
        """会派から政党を削除する.

        Args:
            group_id: 会派ID
            party_id: 政党ID

        Returns:
            削除に成功した場合True
        """
        pass

    @abstractmethod
    async def set_primary(
        self, group_id: int, party_id: int
    ) -> ParliamentaryGroupParty | None:
        """指定した政党を会派の主要政党に設定する.

        既存のis_primary=trueをfalseに更新した上で、指定レコードをtrueに設定する。

        Args:
            group_id: 会派ID
            party_id: 政党ID

        Returns:
            更新された関連エンティティ、存在しない場合はNone
        """
        pass
