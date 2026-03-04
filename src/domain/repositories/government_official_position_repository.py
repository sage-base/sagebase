from abc import abstractmethod
from datetime import date

from src.domain.entities.government_official_position import GovernmentOfficialPosition
from src.domain.repositories.base import BaseRepository


class GovernmentOfficialPositionRepository(
    BaseRepository[GovernmentOfficialPosition],
):
    """政府関係者の役職履歴リポジトリのインターフェース."""

    @abstractmethod
    async def get_by_official(
        self, government_official_id: int
    ) -> list[GovernmentOfficialPosition]:
        """政府関係者IDで役職履歴を取得する."""
        pass

    @abstractmethod
    async def get_active_by_official(
        self, government_official_id: int, as_of_date: date | None = None
    ) -> list[GovernmentOfficialPosition]:
        """政府関係者IDで有効な役職を取得する."""
        pass

    @abstractmethod
    async def bulk_upsert(
        self, positions: list[GovernmentOfficialPosition]
    ) -> list[GovernmentOfficialPosition]:
        """役職履歴を一括upsertする.

        official_id + organization + position + start_date の組み合わせで
        既存チェックを行い、存在すれば更新、なければ新規作成する。
        """
        pass
