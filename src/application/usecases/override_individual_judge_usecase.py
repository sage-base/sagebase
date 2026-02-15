"""記名投票による個人データ上書きUseCase."""

import csv
import io
import logging

from dataclasses import dataclass
from datetime import date

from src.application.dtos.override_individual_judge_dto import (
    DefectionItem,
    IndividualVoteInputItem,
    OverrideIndividualJudgeRequestDTO,
    OverrideIndividualJudgeResultDTO,
)
from src.domain.entities.proposal_judge import JudgmentType, ProposalJudge
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

_VALID_JUDGMENTS = {jt.value for jt in JudgmentType}


@dataclass
class _GroupContext:
    """会派賛否コンテキスト（内部用）."""

    pg_judgment_map: dict[int, str]
    politician_to_pg: dict[int, int]
    pg_name_map: dict[int, str]


class OverrideIndividualJudgeUseCase:
    """記名投票の実データで個人投票データを上書きするUseCase."""

    def __init__(
        self,
        proposal_judge_repository: ProposalJudgeRepository,
        group_judge_repository: ProposalParliamentaryGroupJudgeRepository,
        politician_repository: PoliticianRepository,
        membership_repository: ParliamentaryGroupMembershipRepository,
        parliamentary_group_repository: ParliamentaryGroupRepository,
        proposal_repository: ProposalRepository,
        meeting_repository: MeetingRepository,
        deliberation_repository: ProposalDeliberationRepository,
    ) -> None:
        self._proposal_judge_repo = proposal_judge_repository
        self._group_judge_repo = group_judge_repository
        self._politician_repo = politician_repository
        self._membership_repo = membership_repository
        self._pg_repo = parliamentary_group_repository
        self._proposal_repo = proposal_repository
        self._meeting_repo = meeting_repository
        self._deliberation_repo = deliberation_repository

    async def execute(
        self, request: OverrideIndividualJudgeRequestDTO
    ) -> OverrideIndividualJudgeResultDTO:
        """記名投票データで個人投票を上書きする."""
        result = OverrideIndividualJudgeResultDTO(success=True)

        # 重複politician_idのバリデーション
        seen_ids: set[int] = set()
        for vote in request.votes:
            if vote.politician_id in seen_ids:
                result.success = False
                result.errors.append(
                    f"重複したpolitician_idがあります: {vote.politician_id}"
                )
                return result
            seen_ids.add(vote.politician_id)

        try:
            group_judges = await self._group_judge_repo.get_by_proposal(
                request.proposal_id
            )
        except Exception as e:
            logger.error("会派賛否の取得に失敗: %s", e)
            result.success = False
            result.errors.append(f"会派賛否の取得に失敗: {e}")
            return result

        meeting_date = await self._get_meeting_date(request.proposal_id)
        ctx = await self._build_group_context(group_judges, meeting_date)

        # 既存の個人投票を一括取得してdict化 (N+1回避)
        existing_judges = await self._proposal_judge_repo.get_by_proposal(
            request.proposal_id
        )
        existing_by_politician: dict[int, ProposalJudge] = {
            j.politician_id: j for j in existing_judges
        }

        judges_to_create: list[ProposalJudge] = []
        judges_to_update: list[ProposalJudge] = []

        # 造反検出用に政治家名が必要なIDを収集
        defection_politician_ids: list[int] = []

        for vote in request.votes:
            existing = existing_by_politician.get(vote.politician_id)
            pg_id = ctx.politician_to_pg.get(vote.politician_id)
            group_judgment = ctx.pg_judgment_map.get(pg_id) if pg_id else None

            if existing is not None:
                existing.approve = vote.approve
                existing.source_type = ProposalJudge.SOURCE_TYPE_ROLL_CALL
                existing.is_defection = existing.compute_defection(group_judgment)
                judges_to_update.append(existing)
            else:
                judge = ProposalJudge(
                    proposal_id=request.proposal_id,
                    politician_id=vote.politician_id,
                    approve=vote.approve,
                    source_type=ProposalJudge.SOURCE_TYPE_ROLL_CALL,
                )
                judge.is_defection = judge.compute_defection(group_judgment)
                judges_to_create.append(judge)

            # 造反候補を記録
            if pg_id is not None and group_judgment is not None:
                if vote.approve != group_judgment:
                    defection_politician_ids.append(vote.politician_id)

        if judges_to_create:
            await self._proposal_judge_repo.bulk_create(judges_to_create)
            result.judges_created = len(judges_to_create)

        if judges_to_update:
            await self._proposal_judge_repo.bulk_update(judges_to_update)
            result.judges_updated = len(judges_to_update)

        # 造反政治家の名前を一括取得
        politician_name_map: dict[int, str] = {}
        for pid in defection_politician_ids:
            politician = await self._politician_repo.get_by_id(pid)
            politician_name_map[pid] = politician.name if politician else f"ID:{pid}"

        # 造反リスト生成
        vote_map = {v.politician_id: v.approve for v in request.votes}
        for pid in defection_politician_ids:
            pg_id = ctx.politician_to_pg[pid]
            group_judgment = ctx.pg_judgment_map[pg_id]
            result.defections.append(
                DefectionItem(
                    politician_id=pid,
                    politician_name=politician_name_map[pid],
                    individual_vote=vote_map[pid],
                    group_judgment=group_judgment,
                    parliamentary_group_name=ctx.pg_name_map.get(pg_id, f"ID:{pg_id}"),
                )
            )

        return result

    async def detect_defections(self, proposal_id: int) -> list[DefectionItem]:
        """既存の個人投票データから造反を検出する."""
        judges = await self._proposal_judge_repo.get_by_proposal(proposal_id)
        group_judges = await self._group_judge_repo.get_by_proposal(proposal_id)

        meeting_date = await self._get_meeting_date(proposal_id)
        ctx = await self._build_group_context(group_judges, meeting_date)

        # 造反候補のpolitician_idを収集
        defection_judges: list[ProposalJudge] = []
        for judge in judges:
            if judge.approve is None:
                continue
            pg_id = ctx.politician_to_pg.get(judge.politician_id)
            if pg_id is None:
                continue
            group_judgment = ctx.pg_judgment_map.get(pg_id)
            if group_judgment is None:
                continue
            if judge.approve != group_judgment:
                defection_judges.append(judge)

        # 造反政治家の名前を一括取得
        politician_name_map: dict[int, str] = {}
        for judge in defection_judges:
            politician = await self._politician_repo.get_by_id(judge.politician_id)
            politician_name_map[judge.politician_id] = (
                politician.name if politician else f"ID:{judge.politician_id}"
            )

        defections: list[DefectionItem] = []
        for judge in defection_judges:
            pg_id = ctx.politician_to_pg[judge.politician_id]
            group_judgment = ctx.pg_judgment_map[pg_id]
            defections.append(
                DefectionItem(
                    politician_id=judge.politician_id,
                    politician_name=politician_name_map[judge.politician_id],
                    individual_vote=judge.approve,  # type: ignore[arg-type]
                    group_judgment=group_judgment,
                    parliamentary_group_name=ctx.pg_name_map.get(pg_id, f"ID:{pg_id}"),
                )
            )

        return defections

    @staticmethod
    def parse_csv(csv_content: str) -> list[IndividualVoteInputItem]:
        """CSVコンテンツをパースして投票入力リストに変換する."""
        reader = csv.reader(io.StringIO(csv_content))
        items: list[IndividualVoteInputItem] = []
        for row in reader:
            if len(row) < 2:
                continue
            politician_id_str = row[0].strip()
            approve = row[1].strip()
            if not politician_id_str:
                continue
            try:
                politician_id = int(politician_id_str)
            except ValueError as e:
                raise ValueError(
                    f"politician_idが整数ではありません: {politician_id_str}"
                ) from e
            if approve not in _VALID_JUDGMENTS:
                raise ValueError(
                    f"不正な賛否値です: {approve} "
                    f"(有効値: {', '.join(sorted(_VALID_JUDGMENTS))})"
                )
            items.append(
                IndividualVoteInputItem(politician_id=politician_id, approve=approve)
            )
        return items

    async def _build_group_context(
        self,
        group_judges: list[ProposalParliamentaryGroupJudge],
        meeting_date: date | None,
    ) -> _GroupContext:
        """会派賛否のコンテキスト情報を構築する."""
        pg_judgment_map: dict[int, str] = {}
        politician_to_pg: dict[int, int] = {}
        pg_name_map: dict[int, str] = {}

        for gj in group_judges:
            if not gj.is_parliamentary_group_judge():
                continue
            for pg_id in gj.parliamentary_group_ids:
                pg_judgment_map[pg_id] = gj.judgment

                pg = await self._pg_repo.get_by_id(pg_id)
                if pg:
                    pg_name_map[pg_id] = pg.name

                if meeting_date:
                    members = await self._membership_repo.get_active_by_group(
                        pg_id, as_of_date=meeting_date
                    )
                    for m in members:
                        politician_to_pg[m.politician_id] = pg_id

        return _GroupContext(
            pg_judgment_map=pg_judgment_map,
            politician_to_pg=politician_to_pg,
            pg_name_map=pg_name_map,
        )

    async def _get_meeting_date(self, proposal_id: int) -> date | None:
        """Proposal→Meeting→dateで投票日を特定する."""
        deliberations = await self._deliberation_repo.get_by_proposal_id(proposal_id)
        for d in deliberations:
            if d.meeting_id is not None:
                meeting = await self._meeting_repo.get_by_id(d.meeting_id)
                if meeting and meeting.date:
                    return meeting.date

        proposal = await self._proposal_repo.get_by_id(proposal_id)
        if proposal is None:
            return None

        if proposal.meeting_id is not None:
            meeting = await self._meeting_repo.get_by_id(proposal.meeting_id)
            if meeting is not None and meeting.date is not None:
                return meeting.date

        if proposal.voted_date is not None:
            return proposal.voted_date

        return None
