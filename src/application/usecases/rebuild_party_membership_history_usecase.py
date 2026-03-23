"""政党所属履歴再構築ユースケース.

選挙データ (election_members) の政党情報から
party_membership_history を再構築する。
"""

import logging

from datetime import date, timedelta
from itertools import groupby

from src.application.dtos.rebuild_party_membership_dto import (
    RebuildPartyMembershipInputDto,
    RebuildPartyMembershipOutputDto,
)
from src.domain.entities.election_member import ElectionMember
from src.domain.entities.party_membership_history import PartyMembershipHistory
from src.domain.repositories.election_member_repository import ElectionMemberRepository
from src.domain.repositories.party_membership_history_repository import (
    PartyMembershipHistoryRepository,
)


logger = logging.getLogger(__name__)


class RebuildPartyMembershipHistoryUseCase:
    """選挙データから政党所属履歴を再構築するユースケース."""

    def __init__(
        self,
        election_member_repository: ElectionMemberRepository,
        party_membership_history_repository: PartyMembershipHistoryRepository,
    ) -> None:
        self._election_member_repo = election_member_repository
        self._party_membership_repo = party_membership_history_repository

    async def execute(
        self, input_dto: RebuildPartyMembershipInputDto
    ) -> RebuildPartyMembershipOutputDto:
        """政党所属履歴を再構築する."""
        output = RebuildPartyMembershipOutputDto(dry_run=input_dto.dry_run)

        # 全ElectionMemberを選挙日付つきで取得（politician_id, election_date昇順）
        all_members_with_dates = (
            await self._election_member_repo.get_all_with_election_date()
        )

        if not all_members_with_dates:
            logger.info("ElectionMemberが0件のため処理終了")
            return output

        # politician_idでグループ化
        grouped = groupby(
            all_members_with_dates,
            key=lambda x: x[0].politician_id,
        )

        new_histories: list[PartyMembershipHistory] = []

        for politician_id, group_iter in grouped:
            entries: list[tuple[ElectionMember, date]] = list(group_iter)
            output.total_politicians += 1

            histories = self._build_histories_for_politician(
                politician_id, entries, output
            )
            new_histories.extend(histories)

        logger.info(
            "再構築結果: 対象政治家=%d, 政党変更あり=%d, 政党情報なし=%d, "
            "新規レコード=%d",
            output.total_politicians,
            output.politicians_with_party_change,
            output.skipped_no_party,
            len(new_histories),
        )

        if input_dto.dry_run:
            output.created_new_records = len(new_histories)
            logger.info("dry_runモードのためDB操作はスキップ")
            return output

        # 既存レコードを全削除
        existing = await self._party_membership_repo.get_all()
        output.deleted_old_records = len(existing)
        for record in existing:
            if record.id is not None:
                await self._party_membership_repo.delete(record.id)

        # 新規レコードを作成
        for history in new_histories:
            await self._party_membership_repo.create(history)
        output.created_new_records = len(new_histories)

        logger.info(
            "DB更新完了: 削除=%d, 作成=%d",
            output.deleted_old_records,
            output.created_new_records,
        )

        return output

    def _build_histories_for_politician(
        self,
        politician_id: int,
        entries: list[tuple[ElectionMember, date]],
        output: RebuildPartyMembershipOutputDto,
    ) -> list[PartyMembershipHistory]:
        """1人の政治家の選挙履歴から所属履歴レコードを構築する."""
        # political_party_idが非NULL かつ election_dateが非NULLの行のみ抽出
        valid_entries = []
        for member, election_date in entries:
            if election_date is None:
                logger.warning(
                    "election_dateがNULLのためスキップ: "
                    "politician_id=%d, election_id=%d",
                    politician_id,
                    member.election_id,
                )
                continue
            if member.political_party_id is None:
                continue
            valid_entries.append((member, election_date))

        if not valid_entries:
            output.skipped_no_party += 1
            return []

        histories: list[PartyMembershipHistory] = []
        current_party_id = valid_entries[0][0].political_party_id
        current_start_date = valid_entries[0][1]
        has_party_change = False

        for member, election_date in valid_entries[1:]:
            if member.political_party_id != current_party_id:
                # 政党変更: 旧レコードにend_dateを設定して確定
                assert current_party_id is not None
                end_date = election_date - timedelta(days=1)
                histories.append(
                    PartyMembershipHistory(
                        politician_id=politician_id,
                        political_party_id=current_party_id,
                        start_date=current_start_date,
                        end_date=end_date,
                    )
                )
                # 新しい政党の開始
                current_party_id = member.political_party_id
                current_start_date = election_date
                has_party_change = True

        # 最後の所属レコード（end_date=None = 現在も所属）
        assert current_party_id is not None
        histories.append(
            PartyMembershipHistory(
                politician_id=politician_id,
                political_party_id=current_party_id,
                start_date=current_start_date,
                end_date=None,
            )
        )

        if has_party_change:
            output.politicians_with_party_change += 1

        return histories
