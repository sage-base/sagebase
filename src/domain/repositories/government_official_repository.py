from abc import abstractmethod

from src.domain.entities.government_official import GovernmentOfficial
from src.domain.repositories.base import BaseRepository


class GovernmentOfficialRepository(BaseRepository[GovernmentOfficial]):
    """政府関係者リポジトリのインターフェース."""

    @abstractmethod
    async def get_by_name(self, name: str) -> GovernmentOfficial | None:
        """名前で政府関係者を取得する."""
        pass

    @abstractmethod
    async def search_by_name(self, name: str) -> list[GovernmentOfficial]:
        """名前の部分一致で政府関係者を検索する."""
        pass
