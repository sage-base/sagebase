"""政治家の政党所属履歴エンティティ."""

from datetime import date, datetime

from src.domain.entities.base import BaseEntity


class PartyMembershipHistory(BaseEntity):
    """政治家の政党所属履歴を表すエンティティ.

    政治家がどの政党にいつからいつまで所属していたかを
    時系列で管理する。
    """

    def __init__(
        self,
        politician_id: int,
        political_party_id: int,
        start_date: date,
        end_date: date | None = None,
        created_at: datetime | None = None,
        updated_at: datetime | None = None,
        id: int | None = None,
    ) -> None:
        super().__init__(id)
        self.politician_id = politician_id
        self.political_party_id = political_party_id
        self.start_date = start_date
        self.end_date = end_date
        self.created_at = created_at
        self.updated_at = updated_at

    def is_active(self, as_of_date: date | None = None) -> bool:
        """指定日時点で所属が有効かどうかを返す."""
        if as_of_date is None:
            as_of_date = date.today()

        if self.start_date > as_of_date:
            return False

        if self.end_date is None:
            return True

        return self.end_date >= as_of_date

    def overlaps_with(self, start_date: date, end_date: date | None = None) -> bool:
        """指定期間と重複するかどうかを返す."""
        if end_date and self.start_date > end_date:
            return False

        if self.end_date and self.end_date < start_date:
            return False

        return True
