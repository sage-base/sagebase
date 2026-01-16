"""Minutes entity."""

from datetime import datetime

from src.domain.entities.base import BaseEntity


class Minutes(BaseEntity):
    """議事録を表すエンティティ."""

    def __init__(
        self,
        meeting_id: int,
        url: str | None = None,
        processed_at: datetime | None = None,
        role_name_mappings: dict[str, str] | None = None,
        id: int | None = None,
    ) -> None:
        super().__init__(id)
        self.meeting_id = meeting_id
        self.url = url
        self.processed_at = processed_at
        self.role_name_mappings = role_name_mappings

    def __str__(self) -> str:
        return f"Minutes for meeting #{self.meeting_id}"
