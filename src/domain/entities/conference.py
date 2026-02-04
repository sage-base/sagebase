"""Conference entity."""

from src.domain.entities.base import BaseEntity


class Conference(BaseEntity):
    """会議体（議会、委員会）を表すエンティティ."""

    def __init__(
        self,
        name: str,
        governing_body_id: int,
        members_introduction_url: str | None = None,
        prefecture: str | None = None,
        term: str | None = None,
        election_cycle_years: int | None = None,
        base_election_year: int | None = None,
        term_number_at_base: int | None = None,
        id: int | None = None,
    ) -> None:
        super().__init__(id)
        self.name = name
        self.governing_body_id = governing_body_id
        self.members_introduction_url = members_introduction_url
        self.prefecture = prefecture
        self.term = term
        self.election_cycle_years = election_cycle_years
        self.base_election_year = base_election_year
        self.term_number_at_base = term_number_at_base

    def __str__(self) -> str:
        return self.name
