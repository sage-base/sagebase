from src.domain.entities.base import BaseEntity


class GovernmentOfficial(BaseEntity):
    """政府関係者（政府参考人・官僚）を表すエンティティ."""

    def __init__(
        self,
        name: str,
        name_yomi: str | None = None,
        id: int | None = None,
    ) -> None:
        super().__init__(id)
        self.name = name
        self.name_yomi = name_yomi
