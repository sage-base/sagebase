"""Parliamentary group entity."""

from datetime import date

from src.domain.entities.base import BaseEntity


class ParliamentaryGroup(BaseEntity):
    """議員団（会派）を表すエンティティ."""

    def __init__(
        self,
        name: str,
        governing_body_id: int,
        url: str | None = None,
        description: str | None = None,
        is_active: bool = True,
        political_party_id: int | None = None,
        chamber: str = "",
        start_date: date | None = None,
        end_date: date | None = None,
        id: int | None = None,
    ) -> None:
        super().__init__(id)
        if end_date is not None and start_date is not None and end_date < start_date:
            msg = (
                f"end_date ({end_date}) は "
                f"start_date ({start_date}) より前にはできません"
            )
            raise ValueError(msg)
        self.name = name
        self.governing_body_id = governing_body_id
        self.url = url
        self.description = description
        self.is_active = is_active
        self.political_party_id = political_party_id
        self.chamber = chamber
        self.start_date = start_date
        self.end_date = end_date

    def is_active_as_of(self, as_of_date: date) -> bool:
        """指定日時点で会派が有効かどうかを返す.

        start_date/end_dateが設定されている場合は日付で判定し、
        未設定の場合はis_activeフラグにフォールバックする。
        """
        if self.start_date is None and self.end_date is None:
            return self.is_active

        if self.start_date is not None and as_of_date < self.start_date:
            return False

        if self.end_date is not None and as_of_date > self.end_date:
            return False

        return True

    def update_period(self, start_date: date | None, end_date: date | None) -> None:
        """有効期間を更新する.

        __init__と同じバリデーションを適用する。
        """
        if end_date is not None and start_date is not None and end_date < start_date:
            msg = (
                f"end_date ({end_date}) は "
                f"start_date ({start_date}) より前にはできません"
            )
            raise ValueError(msg)
        self.start_date = start_date
        self.end_date = end_date

    def overlaps_with(self, start_date: date, end_date: date | None = None) -> bool:
        """指定期間と重複するかどうかを返す.

        self.start_date/self.end_dateが両方未設定の場合はis_activeフラグにフォールバックする。
        引数のend_date=Noneは「現在も継続中（開放区間）」を意味する。
        """
        if self.start_date is None and self.end_date is None:
            return self.is_active

        if end_date is not None and self.start_date is not None:
            if self.start_date > end_date:
                return False

        if self.end_date is not None and self.end_date < start_date:
            return False

        return True

    def __str__(self) -> str:
        return self.name
