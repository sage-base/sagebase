"""Conference entity."""

from src.domain.entities.base import BaseEntity


class Conference(BaseEntity):
    """会議体（議会、委員会）を表すエンティティ."""

    def __init__(
        self,
        name: str,
        governing_body_id: int,
        type: str | None = None,
        members_introduction_url: str | None = None,
        prefecture: str | None = None,
        id: int | None = None,
    ) -> None:
        super().__init__(id)
        self.name = name
        self.governing_body_id = governing_body_id
        self.type = type
        self.members_introduction_url = members_introduction_url
        self.prefecture = prefecture

    def __str__(self) -> str:
        return self.name
