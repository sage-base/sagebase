"""Election repository interface."""

from abc import abstractmethod

from src.domain.entities.election import Election
from src.domain.repositories.base import BaseRepository


class ElectionRepository(BaseRepository[Election]):
    """Repository interface for elections."""

    @abstractmethod
    async def get_by_governing_body(self, governing_body_id: int) -> list[Election]:
        """開催主体に属する全選挙を取得.

        Args:
            governing_body_id: 開催主体ID

        Returns:
            選挙エンティティのリスト（選挙日の降順）
        """
        pass

    @abstractmethod
    async def get_by_governing_body_and_term(
        self,
        governing_body_id: int,
        term_number: int,
        election_type: str | None = None,
    ) -> Election | None:
        """開催主体と期番号で選挙を取得.

        Args:
            governing_body_id: 開催主体ID
            term_number: 期番号
            election_type: 選挙種別（指定時はさらに絞り込む）

        Returns:
            選挙エンティティ、見つからない場合はNone
        """
        pass
