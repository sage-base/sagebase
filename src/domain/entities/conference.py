"""Conference entity."""

from src.domain.entities.base import BaseEntity


class Conference(BaseEntity):
    """会議体（議会、委員会）を表すエンティティ."""

    def __init__(
        self,
        name: str,
        governing_body_id: int,
        term: str | None = None,
        election_id: int | None = None,
        id: int | None = None,
    ) -> None:
        super().__init__(id)
        self.name = name
        self.governing_body_id = governing_body_id
        self.term = term
        self.election_id = election_id

    def __str__(self) -> str:
        return self.name
