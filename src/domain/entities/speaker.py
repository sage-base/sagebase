"""Speaker entity."""

from datetime import datetime
from uuid import UUID

from src.domain.entities.base import BaseEntity


class Speaker(BaseEntity):
    """発言者を表すエンティティ.

    VerifiableEntityプロトコルを実装し、手動検証状態と
    LLM抽出ログ参照を保持する。
    """

    def __init__(
        self,
        name: str,
        type: str | None = None,
        political_party_name: str | None = None,
        position: str | None = None,
        is_politician: bool = False,
        politician_id: int | None = None,
        matched_by_user_id: UUID | None = None,
        is_manually_verified: bool = False,
        latest_extraction_log_id: int | None = None,
        created_at: datetime | None = None,
        updated_at: datetime | None = None,
        id: int | None = None,
    ) -> None:
        super().__init__(id)
        self.name = name
        self.type = type
        self.political_party_name = political_party_name
        self.position = position
        self.is_politician = is_politician
        self.politician_id = politician_id
        self.matched_by_user_id = matched_by_user_id
        self.is_manually_verified = is_manually_verified
        self.latest_extraction_log_id = latest_extraction_log_id
        self.created_at = created_at
        self.updated_at = updated_at

    def mark_as_manually_verified(self) -> None:
        """手動検証済みとしてマークする."""
        self.is_manually_verified = True

    def update_from_extraction_log(self, log_id: int) -> None:
        """最新の抽出ログIDを更新する."""
        self.latest_extraction_log_id = log_id

    def can_be_updated_by_ai(self) -> bool:
        """AIによる更新が可能かどうかを返す."""
        return not self.is_manually_verified

    def __str__(self) -> str:
        parts = [self.name]
        if self.position:
            parts.append(f"({self.position})")
        if self.political_party_name:
            parts.append(f"- {self.political_party_name}")
        return " ".join(parts)
