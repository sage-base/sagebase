"""会派と政党の多対多関連エンティティ."""

from src.domain.entities.base import BaseEntity


class ParliamentaryGroupParty(BaseEntity):
    """会派と政党の多対多関連を表すエンティティ."""

    def __init__(
        self,
        parliamentary_group_id: int,
        political_party_id: int,
        is_primary: bool = False,
        id: int | None = None,
    ) -> None:
        super().__init__(id)
        self.parliamentary_group_id = parliamentary_group_id
        self.political_party_id = political_party_id
        self.is_primary = is_primary
