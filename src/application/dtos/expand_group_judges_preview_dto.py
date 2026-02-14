"""会派賛否展開プレビュー用DTO."""

from dataclasses import dataclass, field


@dataclass
class GroupJudgePreviewMember:
    """プレビュー対象メンバー."""

    politician_id: int
    politician_name: str
    has_existing_vote: bool


@dataclass
class GroupJudgePreviewItem:
    """個別の会派賛否プレビュー."""

    group_judge_id: int
    judgment: str
    parliamentary_group_names: list[str]
    members: list[GroupJudgePreviewMember]
    errors: list[str] = field(default_factory=list)


@dataclass
class ExpandGroupJudgesPreviewDTO:
    """会派賛否展開プレビュー結果DTO."""

    success: bool
    items: list[GroupJudgePreviewItem] = field(default_factory=list)
    total_members: int = 0
    total_existing_votes: int = 0
    errors: list[str] = field(default_factory=list)
