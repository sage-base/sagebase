"""政党所属議員の会派自動紐付けユースケース.

選挙で当選した政党所属議員を、party_membership_history の政党所属に基づいて
会派（parliamentary_group）に自動紐付けする。

処理フロー:
    1. 選挙を term_number で検索
    2. 当選者の election_member を取得
    3. 各議員の政党所属を party_membership_history から確認
    4. parliamentary_groups で political_party_id 一致 + active の会派を検索
    5. 1:1 マッチなら parliamentary_group_memberships を作成
"""

import logging

from collections import defaultdict
from datetime import date

from src.application.dtos.parliamentary_group_linkage_dto import (
    LinkedMember,
    LinkParliamentaryGroupInputDto,
    LinkParliamentaryGroupOutputDto,
    SkippedMember,
)
from src.domain.entities.parliamentary_group import ParliamentaryGroup
from src.domain.repositories.election_member_repository import ElectionMemberRepository
from src.domain.repositories.election_repository import ElectionRepository
from src.domain.repositories.parliamentary_group_membership_repository import (
    ParliamentaryGroupMembershipRepository,
)
from src.domain.repositories.parliamentary_group_repository import (
    ParliamentaryGroupRepository,
)
from src.domain.repositories.party_membership_history_repository import (
    PartyMembershipHistoryRepository,
)
from src.domain.repositories.politician_repository import PoliticianRepository


logger = logging.getLogger(__name__)


class LinkParliamentaryGroupUseCase:
    """政党所属議員の会派自動紐付けユースケース."""

    def __init__(
        self,
        election_repository: ElectionRepository,
        election_member_repository: ElectionMemberRepository,
        politician_repository: PoliticianRepository,
        parliamentary_group_repository: ParliamentaryGroupRepository,
        parliamentary_group_membership_repository: (
            ParliamentaryGroupMembershipRepository
        ),
        party_membership_history_repository: (
            PartyMembershipHistoryRepository | None
        ) = None,
    ) -> None:
        self._election_repo = election_repository
        self._member_repo = election_member_repository
        self._politician_repo = politician_repository
        self._group_repo = parliamentary_group_repository
        self._membership_repo = parliamentary_group_membership_repository
        self._party_history_repo = party_membership_history_repository

    async def execute(
        self,
        input_dto: LinkParliamentaryGroupInputDto,
    ) -> LinkParliamentaryGroupOutputDto:
        """会派紐付けを実行する."""
        output = LinkParliamentaryGroupOutputDto()

        # 1. 選挙を取得
        election = await self._election_repo.get_by_governing_body_and_term(
            input_dto.governing_body_id, input_dto.term_number
        )
        if election is None or election.id is None:
            output.errors = 1
            output.error_details.append(
                f"第{input_dto.term_number}回の選挙が見つかりません"
            )
            return output

        # 2. 当選者を取得
        all_members = await self._member_repo.get_by_election_id(election.id)
        elected_members = [m for m in all_members if m.is_elected]
        output.total_elected = len(elected_members)

        if not elected_members:
            logger.info("当選者が0件です")
            return output

        # 3. 政治家情報を一括取得
        politician_ids = [m.politician_id for m in elected_members]
        politicians = await self._politician_repo.get_by_ids(politician_ids)
        politician_map = {p.id: p for p in politicians if p.id is not None}

        # 3.5. 選挙日時点の政党所属を一括取得
        history_map = None
        if self._party_history_repo is not None:
            history_map = await self._party_history_repo.get_current_by_politicians(
                politician_ids, as_of_date=election.election_date
            )

        # 4. アクティブな会派を取得し、political_party_id → 会派のマッピングを構築
        groups = await self._group_repo.get_by_governing_body_id(
            input_dto.governing_body_id, active_only=True
        )
        party_to_groups: dict[int, list[ParliamentaryGroup]] = defaultdict(list)
        for group in groups:
            if group.political_party_id is not None:
                party_to_groups[group.political_party_id].append(group)

        # 5. 既存メンバーシップを一括取得して重複チェック用セットを構築
        existing_keys: set[tuple[int, int, date]] = set()
        for group in groups:
            if group.id is None:
                continue
            active_memberships = await self._membership_repo.get_active_by_group(
                group.id, as_of_date=election.election_date
            )
            for ms in active_memberships:
                existing_keys.add(
                    (
                        ms.politician_id,
                        ms.parliamentary_group_id,
                        ms.start_date,
                    )
                )

        # 6. 各当選者を処理
        for member in elected_members:
            politician = politician_map.get(member.politician_id)
            if politician is None:
                output.errors += 1
                output.error_details.append(
                    f"politician_id={member.politician_id}が見つかりません"
                )
                continue

            politician_name = politician.name
            party_id: int | None = None
            if history_map is not None:
                history = history_map.get(member.politician_id)
                if history is not None:
                    party_id = history.political_party_id

            if party_id is None:
                output.skipped_no_party += 1
                output.skipped_members.append(
                    SkippedMember(
                        politician_id=member.politician_id,
                        politician_name=politician_name,
                        reason="政党所属履歴なし",
                    )
                )
                continue

            matching_groups = party_to_groups.get(party_id, [])

            if len(matching_groups) == 0:
                output.skipped_no_group += 1
                output.skipped_members.append(
                    SkippedMember(
                        politician_id=member.politician_id,
                        politician_name=politician_name,
                        reason="対応する会派なし",
                        political_party_id=party_id,
                    )
                )
                continue

            if len(matching_groups) > 1:
                group_names = ", ".join(g.name for g in matching_groups)
                output.skipped_multiple_groups += 1
                output.skipped_members.append(
                    SkippedMember(
                        politician_id=member.politician_id,
                        politician_name=politician_name,
                        reason=f"複数会派: {group_names}",
                        political_party_id=party_id,
                    )
                )
                continue

            # 1:1 マッチ
            target_group = matching_groups[0]
            if target_group.id is None:
                output.errors += 1
                output.error_details.append(f"会派'{target_group.name}'のIDがNullです")
                continue

            was_existing = (
                member.politician_id,
                target_group.id,
                election.election_date,
            ) in existing_keys

            if was_existing:
                output.already_existed_count += 1
            else:
                if not input_dto.dry_run:
                    await self._membership_repo.create_membership(
                        politician_id=member.politician_id,
                        group_id=target_group.id,
                        start_date=election.election_date,
                    )
                output.linked_count += 1

            output.linked_members.append(
                LinkedMember(
                    politician_id=member.politician_id,
                    politician_name=politician_name,
                    parliamentary_group_id=target_group.id,
                    parliamentary_group_name=target_group.name,
                    was_existing=was_existing,
                )
            )

        logger.info(
            "会派紐付け完了: 当選者=%d, 紐付け=%d, 既存=%d, "
            "政党未設定スキップ=%d, 会派なしスキップ=%d, 複数会派スキップ=%d, "
            "エラー=%d",
            output.total_elected,
            output.linked_count,
            output.already_existed_count,
            output.skipped_no_party,
            output.skipped_no_group,
            output.skipped_multiple_groups,
            output.errors,
        )
        return output
