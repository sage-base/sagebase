"""選挙結果メンバーを表すエンティティ."""

from src.domain.entities.base import BaseEntity


class ElectionMember(BaseEntity):
    """選挙結果メンバーを表すエンティティ.

    どの政治家がどの選挙で当選/落選したかを管理する。
    """

    RESULT_ELECTED: str = "当選"
    RESULT_LOST: str = "落選"
    RESULT_PROPORTIONAL_ELECTED: str = "比例当選"
    RESULT_PROPORTIONAL_REVIVAL: str = "比例復活"

    VALID_RESULTS: list[str] = [
        RESULT_ELECTED,
        RESULT_LOST,
        "次点",
        "繰上当選",
        "無投票当選",
        RESULT_PROPORTIONAL_ELECTED,
        RESULT_PROPORTIONAL_REVIVAL,
    ]
    ELECTED_RESULTS: list[str] = [
        RESULT_ELECTED,
        "繰上当選",
        "無投票当選",
        RESULT_PROPORTIONAL_ELECTED,
        RESULT_PROPORTIONAL_REVIVAL,
    ]

    def __init__(
        self,
        election_id: int,
        politician_id: int,
        result: str,
        votes: int | None = None,
        rank: int | None = None,
        id: int | None = None,
    ) -> None:
        """選挙結果メンバーエンティティを初期化する.

        Args:
            election_id: 選挙ID
            politician_id: 政治家ID
            result: 選挙結果（当選, 落選など）
            votes: 得票数
            rank: 順位
            id: 選挙結果メンバーID
        """
        super().__init__(id)
        self.election_id = election_id
        self.politician_id = politician_id
        self.result = result
        self.votes = votes
        self.rank = rank

    def __str__(self) -> str:
        """文字列表現を返す."""
        return (
            f"ElectionMember(election_id={self.election_id}, "
            f"politician_id={self.politician_id}, "
            f"result={self.result})"
        )

    @property
    def is_elected(self) -> bool:
        """当選しているかどうかを判定する."""
        return self.result in self.ELECTED_RESULTS
