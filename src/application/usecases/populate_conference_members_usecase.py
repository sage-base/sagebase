"""選挙当選者→ConferenceMember一括生成ユースケース.

選挙の当選者（election_members, is_elected=true）を
ConferenceMember（politician_affiliations）に一括変換する。
衆議院・参議院の両方に対応。

処理フロー:
    1. 指定回次の選挙を取得
    2. 当選者一覧を取得
    3. 対象会議体を取得
    4. 全選挙から次回選挙日を算出し end_date を決定
       - 衆議院: 同一院の次回選挙日-1
       - 参議院: 半数改選のため同じパリティ（奇偶）の次回選挙日-1
    5. 各当選者に対して conference_member を upsert
"""

import logging

from datetime import date, timedelta

from src.application.dtos.conference_member_population_dto import (
    PopulateConferenceMembersInputDto,
    PopulateConferenceMembersOutputDto,
    PopulatedMember,
)
from src.domain.repositories.conference_member_repository import (
    ConferenceMemberRepository,
)
from src.domain.repositories.conference_repository import ConferenceRepository
from src.domain.repositories.election_member_repository import ElectionMemberRepository
from src.domain.repositories.election_repository import ElectionRepository
from src.domain.repositories.politician_repository import PoliticianRepository


logger = logging.getLogger(__name__)


class PopulateConferenceMembersUseCase:
    """選挙当選者→ConferenceMember一括生成ユースケース."""

    def __init__(
        self,
        election_repository: ElectionRepository,
        election_member_repository: ElectionMemberRepository,
        conference_repository: ConferenceRepository,
        conference_member_repository: ConferenceMemberRepository,
        politician_repository: PoliticianRepository,
    ) -> None:
        self._election_repo = election_repository
        self._election_member_repo = election_member_repository
        self._conference_repo = conference_repository
        self._conference_member_repo = conference_member_repository
        self._politician_repo = politician_repository

    async def execute(
        self,
        input_dto: PopulateConferenceMembersInputDto,
    ) -> PopulateConferenceMembersOutputDto:
        """ConferenceMember一括生成を実行する."""
        output = PopulateConferenceMembersOutputDto()

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
        all_members = await self._election_member_repo.get_by_election_id(election.id)
        elected_members = [m for m in all_members if m.is_elected]
        output.total_elected = len(elected_members)

        if not elected_members:
            logger.info("当選者が0件です")
            return output

        # 3. 会議体を取得
        conference = await self._conference_repo.get_by_name_and_governing_body(
            input_dto.conference_name, input_dto.governing_body_id
        )
        if conference is None or conference.id is None:
            output.errors = 1
            output.error_details.append(
                f"会議体'{input_dto.conference_name}'が見つかりません"
            )
            return output

        # 4. 全選挙から次回選挙日を算出し end_date を決定
        all_elections = await self._election_repo.get_by_governing_body(
            input_dto.governing_body_id
        )
        same_chamber_elections = sorted(
            [e for e in all_elections if e.chamber == election.chamber],
            key=lambda e: e.election_date,
        )

        end_date: date | None = None
        if election.chamber == "参議院":
            # 参議院: 半数改選のため同じパリティ（奇偶）の次回選挙をend_dateに
            same_parity = sorted(
                [
                    e
                    for e in same_chamber_elections
                    if e.term_number % 2 == election.term_number % 2
                ],
                key=lambda e: e.election_date,
            )
            idx = next(
                (
                    i
                    for i, e in enumerate(same_parity)
                    if e.term_number == input_dto.term_number
                ),
                None,
            )
            if idx is not None and idx + 1 < len(same_parity):
                end_date = same_parity[idx + 1].election_date - timedelta(days=1)
        else:
            # 衆議院: 同一院の次回選挙日-1
            current_idx = next(
                (
                    i
                    for i, e in enumerate(same_chamber_elections)
                    if e.term_number == input_dto.term_number
                ),
                None,
            )
            if current_idx is not None and current_idx + 1 < len(
                same_chamber_elections
            ):
                end_date = same_chamber_elections[
                    current_idx + 1
                ].election_date - timedelta(days=1)

        # 5. 政治家情報を一括取得
        politician_ids = [m.politician_id for m in elected_members]
        politicians = await self._politician_repo.get_by_ids(politician_ids)
        politician_map = {p.id: p for p in politicians if p.id is not None}

        # 6. 既存メンバーを取得して重複チェック用セットを構築
        # (politician_id, conference_id, start_date) の3つ組で判定
        # （upsertの一意性キーと一致させる）
        existing_members = await self._conference_member_repo.get_by_conference(
            conference.id, active_only=False
        )
        existing_keys: set[tuple[int, int, date]] = {
            (m.politician_id, m.conference_id, m.start_date) for m in existing_members
        }

        # 7. 各当選者に対して upsert
        for member in elected_members:
            politician = politician_map.get(member.politician_id)
            politician_name = (
                politician.name if politician else f"ID:{member.politician_id}"
            )

            was_existing = (
                member.politician_id,
                conference.id,
                election.election_date,
            ) in existing_keys

            if was_existing:
                output.already_existed_count += 1
            else:
                if not input_dto.dry_run:
                    await self._conference_member_repo.upsert(
                        politician_id=member.politician_id,
                        conference_id=conference.id,
                        start_date=election.election_date,
                        end_date=end_date,
                    )
                output.created_count += 1

            output.populated_members.append(
                PopulatedMember(
                    politician_id=member.politician_id,
                    politician_name=politician_name,
                    start_date=election.election_date,
                    end_date=end_date,
                    was_existing=was_existing,
                )
            )

        logger.info(
            "ConferenceMember生成完了: 当選者=%d, 新規=%d, 既存=%d, エラー=%d",
            output.total_elected,
            output.created_count,
            output.already_existed_count,
            output.errors,
        )
        return output
