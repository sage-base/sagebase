"""Politician entity."""

from src.domain.entities.base import BaseEntity


class Politician(BaseEntity):
    """政治家を表すエンティティ.

    VerifiableEntityプロトコルを実装し、手動検証状態と
    LLM抽出ログ参照を保持する。
    """

    def __init__(
        self,
        name: str,
        political_party_id: int | None = None,
        furigana: str | None = None,
        district: str | None = None,
        profile_page_url: str | None = None,
        party_position: str | None = None,
        is_manually_verified: bool = False,
        latest_extraction_log_id: int | None = None,
        id: int | None = None,
    ) -> None:
        super().__init__(id)
        self.name = name
        self.political_party_id = political_party_id
        self.furigana = furigana
        self.district = district
        self.profile_page_url = profile_page_url
        self.party_position = party_position
        self.is_manually_verified = is_manually_verified
        self.latest_extraction_log_id = latest_extraction_log_id

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
        return self.name
