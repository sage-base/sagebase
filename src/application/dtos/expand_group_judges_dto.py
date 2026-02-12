"""会派賛否から個人投票データへの展開に関するDTO."""

from dataclasses import dataclass, field


@dataclass
class ExpandGroupJudgesRequestDTO:
    """会派賛否展開リクエストDTO."""

    proposal_id: int | None = None
    group_judge_id: int | None = None
    force_overwrite: bool = False


@dataclass
class GroupJudgeExpansionSummary:
    """個別の会派賛否展開結果サマリー."""

    group_judge_id: int
    proposal_id: int
    judgment: str
    parliamentary_group_ids: list[int]
    members_found: int = 0
    judges_created: int = 0
    judges_skipped: int = 0
    judges_overwritten: int = 0
    errors: list[str] = field(default_factory=list)


@dataclass
class ExpandGroupJudgesResultDTO:
    """会派賛否展開結果DTO."""

    success: bool
    total_group_judges_processed: int = 0
    total_members_found: int = 0
    total_judges_created: int = 0
    total_judges_skipped: int = 0
    total_judges_overwritten: int = 0
    group_summaries: list[GroupJudgeExpansionSummary] = field(default_factory=list)
    errors: list[str] = field(default_factory=list)
    skipped_no_meeting_date: int = 0
