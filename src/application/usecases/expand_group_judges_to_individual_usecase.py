"""会派賛否から個人投票データへの展開UseCase."""

import logging

from datetime import date

from src.application.dtos.expand_group_judges_dto import (
    ExpandGroupJudgesRequestDTO,
    ExpandGroupJudgesResultDTO,
    GroupJudgeExpansionSummary,
)
from src.application.dtos.expand_group_judges_preview_dto import (
    ExpandGroupJudgesPreviewDTO,
    GroupJudgePreviewItem,
    GroupJudgePreviewMember,
)
from src.domain.entities.proposal_judge import ProposalJudge
from src.domain.entities.proposal_parliamentary_group_judge import (
    ProposalParliamentaryGroupJudge,
)
from src.domain.repositories.meeting_repository import MeetingRepository
from src.domain.repositories.parliamentary_group_membership_repository import (
    ParliamentaryGroupMembershipRepository,
)
from src.domain.repositories.parliamentary_group_repository import (
    ParliamentaryGroupRepository,
)
from src.domain.repositories.politician_repository import PoliticianRepository
from src.domain.repositories.proposal_deliberation_repository import (
    ProposalDeliberationRepository,
)
from src.domain.repositories.proposal_judge_repository import ProposalJudgeRepository
from src.domain.repositories.proposal_parliamentary_group_judge_repository import (
    ProposalParliamentaryGroupJudgeRepository,
)
from src.domain.repositories.proposal_repository import ProposalRepository


logger = logging.getLogger(__name__)


class ExpandGroupJudgesToIndividualUseCase:
    """会派賛否データから個人投票データを展開するUseCase."""

    def __init__(
        self,
        group_judge_repository: ProposalParliamentaryGroupJudgeRepository,
        proposal_judge_repository: ProposalJudgeRepository,
        membership_repository: ParliamentaryGroupMembershipRepository,
        proposal_repository: ProposalRepository,
        meeting_repository: MeetingRepository,
        politician_repository: PoliticianRepository,
        deliberation_repository: ProposalDeliberationRepository,
        parliamentary_group_repository: ParliamentaryGroupRepository,
    ) -> None:
        self._group_judge_repo = group_judge_repository
        self._proposal_judge_repo = proposal_judge_repository
        self._membership_repo = membership_repository
        self._proposal_repo = proposal_repository
        self._meeting_repo = meeting_repository
        self._politician_repo = politician_repository
        self._deliberation_repo = deliberation_repository
        self._parliamentary_group_repo = parliamentary_group_repository

    async def execute(
        self, request: ExpandGroupJudgesRequestDTO
    ) -> ExpandGroupJudgesResultDTO:
        """会派賛否を個人投票データに展開する."""
        result = ExpandGroupJudgesResultDTO(success=True)

        try:
            group_judges = await self._get_target_group_judges(request)
        except Exception as e:
            logger.error(f"会派賛否の取得に失敗: {e}")
            result.success = False
            result.errors.append(f"会派賛否の取得に失敗: {e}")
            return result

        for gj in group_judges:
            if not gj.is_parliamentary_group_judge():
                continue

            summary = GroupJudgeExpansionSummary(
                group_judge_id=gj.id or 0,
                proposal_id=gj.proposal_id,
                judgment=gj.judgment,
                parliamentary_group_ids=list(gj.parliamentary_group_ids),
            )

            meeting_date = await self._get_meeting_date(gj.proposal_id)
            if meeting_date is None:
                result.skipped_no_meeting_date += 1
                summary.errors.append(
                    "投票日が特定できません（meeting_idまたはdateがnull）"
                )
                result.group_summaries.append(summary)
                continue

            all_politician_ids = await self._resolve_group_members(
                gj.parliamentary_group_ids, meeting_date
            )

            summary.members_found = len(all_politician_ids)

            judges_to_create: list[ProposalJudge] = []
            for politician_id in all_politician_ids:
                existing = (
                    await self._proposal_judge_repo.get_by_proposal_and_politician(
                        gj.proposal_id, politician_id
                    )
                )

                if existing is not None:
                    if request.force_overwrite:
                        existing.approve = gj.judgment
                        existing.source_type = ProposalJudge.SOURCE_TYPE_GROUP_EXPANSION
                        existing.source_group_judge_id = gj.id
                        await self._proposal_judge_repo.update(existing)
                        summary.judges_overwritten += 1
                    else:
                        summary.judges_skipped += 1
                    continue

                judges_to_create.append(
                    ProposalJudge(
                        proposal_id=gj.proposal_id,
                        politician_id=politician_id,
                        approve=gj.judgment,
                        source_type=ProposalJudge.SOURCE_TYPE_GROUP_EXPANSION,
                        source_group_judge_id=gj.id,
                    )
                )

            if judges_to_create:
                await self._proposal_judge_repo.bulk_create(judges_to_create)
                summary.judges_created = len(judges_to_create)

            result.group_summaries.append(summary)
            result.total_group_judges_processed += 1
            result.total_members_found += summary.members_found
            result.total_judges_created += summary.judges_created
            result.total_judges_skipped += summary.judges_skipped
            result.total_judges_overwritten += summary.judges_overwritten

        return result

    async def preview(self, group_judge_ids: list[int]) -> ExpandGroupJudgesPreviewDTO:
        """指定した会派賛否IDリストに対しプレビューを生成する."""
        result = ExpandGroupJudgesPreviewDTO(success=True)

        for gj_id in group_judge_ids:
            gj = await self._group_judge_repo.get_by_id(gj_id)
            if gj is None:
                result.errors.append(f"会派賛否ID {gj_id} が見つかりません")
                continue

            if not gj.is_parliamentary_group_judge():
                continue

            pg_names: list[str] = []
            for pg_id in gj.parliamentary_group_ids:
                pg = await self._parliamentary_group_repo.get_by_id(pg_id)
                pg_names.append(pg.name if pg else f"ID:{pg_id}")

            item = GroupJudgePreviewItem(
                group_judge_id=gj.id or 0,
                judgment=gj.judgment,
                parliamentary_group_names=pg_names,
                members=[],
            )

            meeting_date = await self._get_meeting_date(gj.proposal_id)
            if meeting_date is None:
                item.errors.append(
                    "投票日が特定できません（meeting_idまたはdateがnull）"
                )
                result.items.append(item)
                continue

            all_politician_ids = await self._resolve_group_members(
                gj.parliamentary_group_ids, as_of_date=meeting_date
            )

            for politician_id in sorted(all_politician_ids):
                politician = await self._politician_repo.get_by_id(politician_id)
                politician_name = (
                    politician.name if politician else f"ID:{politician_id}"
                )

                existing = (
                    await self._proposal_judge_repo.get_by_proposal_and_politician(
                        gj.proposal_id, politician_id
                    )
                )
                has_existing = existing is not None

                item.members.append(
                    GroupJudgePreviewMember(
                        politician_id=politician_id,
                        politician_name=politician_name,
                        has_existing_vote=has_existing,
                    )
                )
                result.total_members += 1
                if has_existing:
                    result.total_existing_votes += 1

            result.items.append(item)

        return result

    async def _resolve_group_members(
        self, parliamentary_group_ids: list[int], as_of_date: date
    ) -> set[int]:
        """会派IDリストから所属政治家IDを解決する."""
        all_politician_ids: set[int] = set()
        for group_id in parliamentary_group_ids:
            members = await self._membership_repo.get_active_by_group(
                group_id, as_of_date=as_of_date
            )
            for m in members:
                all_politician_ids.add(m.politician_id)
        return all_politician_ids

    async def _get_target_group_judges(
        self, request: ExpandGroupJudgesRequestDTO
    ) -> list[ProposalParliamentaryGroupJudge]:
        """リクエストに応じて対象の会派賛否を取得する."""
        if request.group_judge_id is not None:
            gj = await self._group_judge_repo.get_by_id(request.group_judge_id)
            return [gj] if gj else []
        elif request.proposal_id is not None:
            return await self._group_judge_repo.get_by_proposal(request.proposal_id)
        else:
            return await self._group_judge_repo.get_all()

    async def _get_meeting_date(self, proposal_id: int) -> date | None:
        """Proposal→Meeting→dateで投票日を特定する."""
        deliberations = await self._deliberation_repo.get_by_proposal_id(proposal_id)
        for d in deliberations:
            if d.meeting_id is not None:
                meeting = await self._meeting_repo.get_by_id(d.meeting_id)
                if meeting and meeting.date:
                    return meeting.date

        proposal = await self._proposal_repo.get_by_id(proposal_id)
        if proposal is None or proposal.meeting_id is None:
            return None

        meeting = await self._meeting_repo.get_by_id(proposal.meeting_id)
        if meeting is None or meeting.date is None:
            return None

        return meeting.date
