"""会派賛否から個人投票データへの展開に関するDTO."""

from __future__ import annotations

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

    def merge(self, other: ExpandGroupJudgesResultDTO) -> None:
        """他の結果DTOを自身にマージする."""
        self.total_group_judges_processed += other.total_group_judges_processed
        self.total_members_found += other.total_members_found
        self.total_judges_created += other.total_judges_created
        self.total_judges_skipped += other.total_judges_skipped
        self.total_judges_overwritten += other.total_judges_overwritten
        self.group_summaries.extend(other.group_summaries)
        self.errors.extend(other.errors)
        self.skipped_no_meeting_date += other.skipped_no_meeting_date
        if not other.success:
            self.success = False


# ========== プレビュー用DTO ==========


@dataclass
class GroupJudgePreviewMember:
    """プレビュー用メンバー情報."""

    politician_id: int
    politician_name: str
    has_existing_vote: bool


@dataclass
class GroupJudgePreviewItem:
    """プレビュー用会派賛否情報."""

    group_judge_id: int
    proposal_id: int
    judgment: str
    parliamentary_group_names: list[str]
    members: list[GroupJudgePreviewMember] = field(default_factory=list)
    existing_vote_count: int = 0
    errors: list[str] = field(default_factory=list)


@dataclass
class ExpandGroupJudgesPreviewDTO:
    """展開プレビュー結果DTO."""

    success: bool
    items: list[GroupJudgePreviewItem] = field(default_factory=list)
    total_members: int = 0
    total_existing_votes: int = 0
    errors: list[str] = field(default_factory=list)
