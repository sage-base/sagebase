"""Conference entity."""

from src.domain.entities.base import BaseEntity


CHAMBER_HOUSE = "衆議院"
CHAMBER_SENATE = "参議院"


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

    @property
    def chamber(self) -> str | None:
        """院名を返す（"衆議院" / "参議院" / None）."""
        if self.name.startswith(CHAMBER_HOUSE):
            return CHAMBER_HOUSE
        if self.name.startswith(CHAMBER_SENATE):
            return CHAMBER_SENATE
        return None

    @property
    def plenary_session_name(self) -> str | None:
        """本会議名を返す（例: "衆議院本会議"）."""
        if self.chamber is None:
            return None
        return f"{self.chamber}本会議"

    def __str__(self) -> str:
        return self.name
