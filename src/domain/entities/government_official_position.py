from datetime import date

from src.domain.entities.base import BaseEntity


class GovernmentOfficialPosition(BaseEntity):
    """政府関係者の役職履歴を表すエンティティ."""

    def __init__(
        self,
        government_official_id: int,
        organization: str,
        position: str,
        start_date: date | None = None,
        end_date: date | None = None,
        source_note: str | None = None,
        id: int | None = None,
    ) -> None:
        super().__init__(id)
        self.government_official_id = government_official_id
        self.organization = organization
        self.position = position
        self.start_date = start_date
        self.end_date = end_date
        self.source_note = source_note

    def is_active(self, as_of_date: date | None = None) -> bool:
        """指定日時点で有効な役職かどうかを判定する."""
        if as_of_date is None:
            return self.end_date is None
        if self.start_date is not None and as_of_date < self.start_date:
            return False
        if self.end_date is not None and as_of_date > self.end_date:
            return False
        return True
