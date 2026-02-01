"""ExtractedConferenceMember entity."""

from datetime import datetime
from enum import Enum

from src.domain.entities.base import BaseEntity


class MatchingStatus(str, Enum):
    """マッチングステータスを表す列挙型."""

    PENDING = "pending"
    MATCHED = "matched"
    NO_MATCH = "no_match"
    NEEDS_REVIEW = "needs_review"


class ExtractedConferenceMember(BaseEntity):
    """会議体メンバー抽出情報を表すエンティティ.

    VerifiableEntityプロトコルを実装し、手動検証状態と
    LLM抽出ログ参照を保持する。
    """

    def __init__(
        self,
        conference_id: int,
        extracted_name: str,
        source_url: str,
        extracted_role: str | None = None,
        extracted_party_name: str | None = None,
        extracted_at: datetime | None = None,
        matched_politician_id: int | None = None,
        matching_confidence: float | None = None,
        matching_status: str = MatchingStatus.PENDING,
        matched_at: datetime | None = None,
        additional_data: str | None = None,
        is_manually_verified: bool = False,
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
        self.matched_politician_id = matched_politician_id
        self.matching_confidence = matching_confidence
        self.matching_status = matching_status
        self.matched_at = matched_at
        self.additional_data = additional_data
        self.is_manually_verified = is_manually_verified
        self.latest_extraction_log_id = latest_extraction_log_id

    def is_matched(self) -> bool:
        """Check if the member has been successfully matched."""
        return self.matching_status == MatchingStatus.MATCHED

    def needs_review(self) -> bool:
        """Check if the member needs manual review."""
        return self.matching_status == MatchingStatus.NEEDS_REVIEW

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
        return (
            f"ExtractedConferenceMember(name={self.extracted_name}, "
            f"status={self.matching_status})"
        )
