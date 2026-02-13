"""議案審議（ProposalDeliberation）エンティティ.

議案と会議の多対多関係を表現するジャンクションテーブルに対応するエンティティ。
1つの議案が複数の会議で審議される場合の紐付けを管理する。
"""

from src.domain.entities.base import BaseEntity


class ProposalDeliberation(BaseEntity):
    """議案審議を表すエンティティ."""

    def __init__(
        self,
        proposal_id: int,
        conference_id: int,
        meeting_id: int | None = None,
        stage: str | None = None,
        id: int | None = None,
    ) -> None:
        super().__init__(id)
        self.proposal_id = proposal_id
        self.conference_id = conference_id
        self.meeting_id = meeting_id
        self.stage = stage

    def __str__(self) -> str:
        stage_str = f" [{self.stage}]" if self.stage else ""
        return (
            f"ProposalDeliberation(proposal={self.proposal_id}, "
            f"conference={self.conference_id}{stage_str})"
        )

    @property
    def has_meeting(self) -> bool:
        return self.meeting_id is not None

    @property
    def has_stage(self) -> bool:
        return self.stage is not None
