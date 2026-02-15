"""記名投票による個人データ上書きに関するDTO."""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass
class IndividualVoteInputItem:
    """個別投票入力項目."""

    politician_id: int
    approve: str


@dataclass
class OverrideIndividualJudgeRequestDTO:
    """記名投票上書きリクエストDTO."""

    proposal_id: int
    votes: list[IndividualVoteInputItem]


@dataclass
class DefectionItem:
    """造反情報."""

    politician_id: int
    politician_name: str
    individual_vote: str
    group_judgment: str
    parliamentary_group_name: str


@dataclass
class OverrideIndividualJudgeResultDTO:
    """記名投票上書き結果DTO."""

    success: bool
    judges_created: int = 0
    judges_updated: int = 0
    judges_skipped: int = 0
    defections: list[DefectionItem] = field(default_factory=list)
    errors: list[str] = field(default_factory=list)
