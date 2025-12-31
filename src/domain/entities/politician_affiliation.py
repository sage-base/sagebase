"""PoliticianAffiliation entity."""

from datetime import date

from src.domain.entities.base import BaseEntity


class PoliticianAffiliation(BaseEntity):
    """政治家の所属を表すエンティティ.

    VerifiableEntityプロトコルを実装し、手動検証状態と
    LLM抽出ログ参照を保持する。
    """

    def __init__(
        self,
        politician_id: int,
        conference_id: int,
        start_date: date,
        end_date: date | None = None,
        role: str | None = None,
        is_manually_verified: bool = False,
        latest_extraction_log_id: int | None = None,
        id: int | None = None,
    ) -> None:
        super().__init__(id)
        self.politician_id = politician_id
        self.conference_id = conference_id
        self.start_date = start_date
        self.end_date = end_date
        self.role = role
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

    def is_active(self) -> bool:
        """Check if the affiliation is currently active."""
        return self.end_date is None

    def __str__(self) -> str:
        status = "active" if self.is_active() else f"ended {self.end_date}"
        return (
            f"PoliticianAffiliation(politician={self.politician_id}, "
            f"conference={self.conference_id}, {status})"
        )
