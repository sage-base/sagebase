"""会派賛否マッチングUseCase.

extracted_proposal_judges（Bronze層）の会派名を
parliamentary_groups（SEED）と突合し、
proposal_parliamentary_group_judges（Gold層）に書き込む。
"""

import logging

from collections import defaultdict
from dataclasses import dataclass

from src.application.dtos.match_proposal_group_judges_dto import (
    MatchProposalGroupJudgesInputDto,
    MatchProposalGroupJudgesOutputDto,
)
from src.domain.entities.proposal_parliamentary_group_judge import (
    ProposalParliamentaryGroupJudge,
)
from src.domain.repositories.extracted_proposal_judge_repository import (
    ExtractedProposalJudgeRepository,
)
from src.domain.repositories.parliamentary_group_repository import (
    ParliamentaryGroupRepository,
)
from src.domain.repositories.proposal_parliamentary_group_judge_repository import (
    ProposalParliamentaryGroupJudgeRepository,
)
from src.domain.value_objects.judge_type import JudgeType


logger = logging.getLogger(__name__)


@dataclass
class _MatchedInfo:
    judge_id: int
    proposal_id: int
    judgment: str
    parliamentary_group_id: int


class MatchProposalGroupJudgesUseCase:
    """会派賛否マッチングUseCase."""

    def __init__(
        self,
        extracted_proposal_judge_repository: ExtractedProposalJudgeRepository,
        parliamentary_group_repository: ParliamentaryGroupRepository,
        proposal_group_judge_repository: ProposalParliamentaryGroupJudgeRepository,
    ) -> None:
        self._extracted_repo = extracted_proposal_judge_repository
        self._group_repo = parliamentary_group_repository
        self._judge_repo = proposal_group_judge_repository

    async def execute(
        self,
        input_dto: MatchProposalGroupJudgesInputDto,
    ) -> MatchProposalGroupJudgesOutputDto:
        output = MatchProposalGroupJudgesOutputDto()

        pending = await self._extracted_repo.get_all_pending()
        group_judges = [j for j in pending if j.extracted_parliamentary_group_name]
        output.total_pending = len(group_judges)

        if not group_judges:
            logger.info("マッチング対象のレコードがありません")
            return output

        groups = await self._group_repo.get_by_governing_body_id(
            input_dto.governing_body_id, active_only=False
        )
        name_to_id: dict[str, int] = {}
        for g in groups:
            if g.id is not None:
                name_to_id[g.name.strip()] = g.id

        logger.info(
            "議員団マスタ: %d件, マッチング対象: %d件",
            len(name_to_id),
            len(group_judges),
        )

        matched_infos: list[_MatchedInfo] = []
        unmatched_set: set[str] = set()

        for judge in group_judges:
            name = judge.extracted_parliamentary_group_name
            if name is None:
                continue
            stripped = name.strip()
            group_id = name_to_id.get(stripped)

            if group_id is not None and judge.id is not None:
                await self._extracted_repo.update_matching_result(
                    judge_id=judge.id,
                    parliamentary_group_id=group_id,
                    confidence=1.0,
                    status="matched",
                )
                matched_infos.append(
                    _MatchedInfo(
                        judge_id=judge.id,
                        proposal_id=judge.proposal_id,
                        judgment=judge.extracted_judgment or "",
                        parliamentary_group_id=group_id,
                    )
                )
                output.matched += 1
            else:
                if judge.id is not None:
                    await self._extracted_repo.update_matching_result(
                        judge_id=judge.id,
                        status="unmatched",
                    )
                unmatched_set.add(stripped)
                output.unmatched += 1

        output.unmatched_names = sorted(unmatched_set)
        if output.unmatched_names:
            logger.warning(
                "マッチングできなかった会派名 (%d種): %s",
                len(output.unmatched_names),
                ", ".join(output.unmatched_names),
            )

        if input_dto.dry_run:
            logger.info("dry_runモード: Gold層への書き込みをスキップ")
            return output

        judges_created = await self._create_gold_layer_judges(matched_infos)
        output.judges_created = judges_created

        return output

    async def _create_gold_layer_judges(
        self,
        matched_infos: list[_MatchedInfo],
    ) -> int:
        if not matched_infos:
            return 0

        grouped: dict[tuple[int, str], list[int]] = defaultdict(list)
        for info in matched_infos:
            key = (info.proposal_id, info.judgment)
            grouped[key].append(info.parliamentary_group_id)

        entities: list[ProposalParliamentaryGroupJudge] = []
        for (proposal_id, judgment), group_ids in grouped.items():
            unique_ids = sorted(set(group_ids))
            entity = ProposalParliamentaryGroupJudge(
                proposal_id=proposal_id,
                judgment=judgment,
                judge_type=JudgeType.PARLIAMENTARY_GROUP,
                parliamentary_group_ids=unique_ids,
            )
            entities.append(entity)

        if entities:
            created = await self._judge_repo.bulk_create(entities)
            logger.info("Gold層に%d件の賛否レコードを作成", len(created))

            for info in matched_infos:
                await self._extracted_repo.mark_processed(info.judge_id)

            return len(created)

        return 0
