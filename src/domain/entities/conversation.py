"""Conversation entity."""

from src.domain.entities.base import BaseEntity


class Conversation(BaseEntity):
    """発言を表すエンティティ.

    VerifiableEntityプロトコルを実装し、手動検証状態と
    LLM抽出ログ参照を保持する。
    """

    def __init__(
        self,
        comment: str,
        sequence_number: int,
        minutes_id: int | None = None,
        speaker_id: int | None = None,
        speaker_name: str | None = None,
        chapter_number: int | None = None,
        sub_chapter_number: int | None = None,
        is_manually_verified: bool = False,
        latest_extraction_log_id: int | None = None,
        id: int | None = None,
    ) -> None:
        super().__init__(id)
        self.comment = comment
        self.sequence_number = sequence_number
        self.minutes_id = minutes_id
        self.speaker_id = speaker_id
        self.speaker_name = speaker_name
        self.chapter_number = chapter_number
        self.sub_chapter_number = sub_chapter_number
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
        speaker = (
            self.speaker_name or f"Speaker #{self.speaker_id}"
            if self.speaker_id
            else "Unknown"
        )
        return (
            f"{speaker}: {self.comment[:50]}..."
            if len(self.comment) > 50
            else f"{speaker}: {self.comment}"
        )
