"""ExtractedConferenceMember entity."""

from datetime import datetime

from src.domain.entities.base import BaseEntity


class ExtractedConferenceMember(BaseEntity):
    """会議体メンバー抽出情報を表すエンティティ.

    Bronze Layer（抽出ログ層）のエンティティとして、
    LLMで抽出された生データを保持する。
    政治家との紐付けはGold Layer（ConferenceMember）で管理される。

    Note:
        VerifiableEntityプロトコルとの互換性のため、is_manually_verifiedと
        mark_as_manually_verified()を実装しているが、Bronze Layerでは
        検証状態を管理しないため、常にFalse/no-opとなる。
    """

    # VerifiableEntityプロトコル互換性のためのダミー属性
    # Bronze Layerでは検証状態を管理しない
    is_manually_verified: bool = False

    def __init__(
        self,
        conference_id: int,
        extracted_name: str,
        source_url: str,
        extracted_role: str | None = None,
        extracted_party_name: str | None = None,
        extracted_at: datetime | None = None,
        additional_data: str | None = None,
        latest_extraction_log_id: int | None = None,
        id: int | None = None,
    ) -> None:
        super().__init__(id)
        self.conference_id = conference_id
        self.extracted_name = extracted_name
        self.source_url = source_url
        self.extracted_role = extracted_role
        self.extracted_party_name = extracted_party_name
        self.extracted_at = extracted_at or datetime.now()
        self.additional_data = additional_data
        self.latest_extraction_log_id = latest_extraction_log_id

    def mark_as_manually_verified(self) -> None:
        """VerifiableEntityプロトコル互換性のためのno-opメソッド.

        Bronze Layerエンティティでは検証状態を管理しないため、
        このメソッドは何もしない。
        """
        pass

    def update_from_extraction_log(self, log_id: int) -> None:
        """最新の抽出ログIDを更新する."""
        self.latest_extraction_log_id = log_id

    def can_be_updated_by_ai(self) -> bool:
        """AIによる更新が可能かどうかを返す.

        Bronze Layerエンティティは常に更新可能。
        検証状態はGold Layer（ConferenceMember）で管理される。
        """
        return True

    def __str__(self) -> str:
        return f"ExtractedConferenceMember(name={self.extracted_name}, id={self.id})"
