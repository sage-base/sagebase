"""ProposalJudge entity module."""

from enum import Enum

from src.domain.entities.base import BaseEntity


class JudgmentType(Enum):
    """議案への判断の種類."""

    APPROVE = "賛成"
    OPPOSE = "反対"
    ABSTAIN = "棄権"
    ABSENT = "欠席"


class ProposalJudge(BaseEntity):
    """議案への賛否情報を表すエンティティ."""

    def __init__(
        self,
        proposal_id: int,
        politician_id: int,
        approve: str | None = None,
        source_type: str | None = None,
        source_group_judge_id: int | None = None,
        id: int | None = None,
    ) -> None:
        super().__init__(id)
        self.proposal_id = proposal_id
        self.politician_id = politician_id
        self.approve = approve
        self.source_type = source_type
        self.source_group_judge_id = source_group_judge_id

    def is_approve(self) -> bool:
        """賛成票かどうかを判定."""
        return self.approve == JudgmentType.APPROVE.value

    def is_oppose(self) -> bool:
        """反対票かどうかを判定."""
        return self.approve == JudgmentType.OPPOSE.value

    def is_abstain(self) -> bool:
        """棄権票かどうかを判定."""
        return self.approve == JudgmentType.ABSTAIN.value

    def is_absent(self) -> bool:
        """欠席かどうかを判定."""
        return self.approve == JudgmentType.ABSENT.value

    def __str__(self) -> str:
        return f"ProposalJudge: Politician {self.politician_id} - {self.approve}"
