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

    @classmethod
    def merge(
        cls, results: list[ExpandGroupJudgesResultDTO]
    ) -> ExpandGroupJudgesResultDTO:
        """複数の結果DTOを1つに統合する."""
        merged = cls(success=all(r.success for r in results))
        for r in results:
            merged.total_group_judges_processed += r.total_group_judges_processed
            merged.total_members_found += r.total_members_found
            merged.total_judges_created += r.total_judges_created
            merged.total_judges_skipped += r.total_judges_skipped
            merged.total_judges_overwritten += r.total_judges_overwritten
            merged.skipped_no_meeting_date += r.skipped_no_meeting_date
            merged.group_summaries.extend(r.group_summaries)
            merged.errors.extend(r.errors)
        return merged
