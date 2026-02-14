"""Election entity."""

from datetime import date

from src.domain.entities.base import BaseEntity


class Election(BaseEntity):
    """選挙を表すエンティティ.

    地方議会の「第n期」は選挙によって決まる。
    選挙をファーストクラスのエンティティとして扱うことで、
    「いつ行われた選挙で決まった期か」が明確になる。
    """

    ELECTION_TYPE_GENERAL = "衆議院議員総選挙"

    def __init__(
        self,
        governing_body_id: int,
        term_number: int,
        election_date: date,
        election_type: str | None = None,
        id: int | None = None,
    ) -> None:
        """選挙エンティティを初期化する.

        Args:
            governing_body_id: 開催主体ID
            term_number: 期番号（例: 21）
            election_date: 選挙実施日
            election_type: 選挙種別（統一地方選挙, 通常選挙, 補欠選挙など）
            id: 選挙ID
        """
        super().__init__(id)
        self.governing_body_id = governing_body_id
        self.term_number = term_number
        self.election_date = election_date
        self.election_type = election_type

    def __str__(self) -> str:
        """文字列表現を返す."""
        return f"第{self.term_number}期 ({self.election_date})"
