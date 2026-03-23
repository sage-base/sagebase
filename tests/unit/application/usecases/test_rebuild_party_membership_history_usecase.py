"""政党所属履歴再構築ユースケースのテスト."""

from datetime import date, timedelta
from unittest.mock import AsyncMock

import pytest

from src.application.dtos.rebuild_party_membership_dto import (
    RebuildPartyMembershipInputDto,
)
from src.application.usecases.rebuild_party_membership_history_usecase import (
    RebuildPartyMembershipHistoryUseCase,
)
from src.domain.entities.election_member import ElectionMember
from src.domain.entities.party_membership_history import PartyMembershipHistory
from src.domain.repositories.election_member_repository import (
    ElectionMemberRepository,
)
from src.domain.repositories.party_membership_history_repository import (
    PartyMembershipHistoryRepository,
)


def _make_member(
    politician_id: int,
    political_party_id: int | None,
    election_id: int = 1,
) -> ElectionMember:
    """テスト用ElectionMemberを生成する."""
    return ElectionMember(
        id=election_id * 100 + politician_id,
        election_id=election_id,
        politician_id=politician_id,
        result="当選",
        political_party_id=political_party_id,
    )


class TestRebuildPartyMembershipHistoryUseCase:
    """再構築ユースケースのテスト."""

    @pytest.fixture()
    def mock_election_member_repo(self) -> AsyncMock:
        return AsyncMock(spec=ElectionMemberRepository)

    @pytest.fixture()
    def mock_party_membership_repo(self) -> AsyncMock:
        return AsyncMock(spec=PartyMembershipHistoryRepository)

    @pytest.fixture()
    def usecase(
        self,
        mock_election_member_repo: AsyncMock,
        mock_party_membership_repo: AsyncMock,
    ) -> RebuildPartyMembershipHistoryUseCase:
        return RebuildPartyMembershipHistoryUseCase(
            election_member_repository=mock_election_member_repo,
            party_membership_history_repository=mock_party_membership_repo,
        )

    @pytest.mark.asyncio()
    async def test_party_change_detection(
        self,
        usecase: RebuildPartyMembershipHistoryUseCase,
        mock_election_member_repo: AsyncMock,
        mock_party_membership_repo: AsyncMock,
    ) -> None:
        """政党変更を検出して2レコード作成、1件目にend_dateが設定される."""
        date1 = date(2012, 12, 16)
        date2 = date(2017, 10, 22)
        # 政治家1: 政党X(id=10) → 政党Y(id=20)
        mock_election_member_repo.get_all_with_election_date.return_value = [
            (
                _make_member(politician_id=1, political_party_id=10, election_id=1),
                date1,
            ),
            (
                _make_member(politician_id=1, political_party_id=20, election_id=2),
                date2,
            ),
        ]
        mock_party_membership_repo.get_all.return_value = []

        result = await usecase.execute(RebuildPartyMembershipInputDto(dry_run=False))

        assert result.total_politicians == 1
        assert result.politicians_with_party_change == 1
        assert result.created_new_records == 2

        # createに渡されたエンティティを検証
        calls = mock_party_membership_repo.create.call_args_list
        assert len(calls) == 2

        first: PartyMembershipHistory = calls[0][0][0]
        assert first.politician_id == 1
        assert first.political_party_id == 10
        assert first.start_date == date1
        assert first.end_date == date2 - timedelta(days=1)

        second: PartyMembershipHistory = calls[1][0][0]
        assert second.politician_id == 1
        assert second.political_party_id == 20
        assert second.start_date == date2
        assert second.end_date is None

    @pytest.mark.asyncio()
    async def test_same_party_multiple_elections(
        self,
        usecase: RebuildPartyMembershipHistoryUseCase,
        mock_election_member_repo: AsyncMock,
        mock_party_membership_repo: AsyncMock,
    ) -> None:
        """同一政党で3回出馬した場合、1レコードにまとめられる."""
        dates = [date(2009, 8, 30), date(2012, 12, 16), date(2017, 10, 22)]
        mock_election_member_repo.get_all_with_election_date.return_value = [
            (_make_member(politician_id=1, political_party_id=10, election_id=i + 1), d)
            for i, d in enumerate(dates)
        ]
        mock_party_membership_repo.get_all.return_value = []

        result = await usecase.execute(RebuildPartyMembershipInputDto(dry_run=False))

        assert result.total_politicians == 1
        assert result.politicians_with_party_change == 0
        assert result.created_new_records == 1

        created: PartyMembershipHistory = (
            mock_party_membership_repo.create.call_args_list[0][0][0]
        )
        assert created.political_party_id == 10
        assert created.start_date == dates[0]
        assert created.end_date is None

    @pytest.mark.asyncio()
    async def test_skip_no_party(
        self,
        usecase: RebuildPartyMembershipHistoryUseCase,
        mock_election_member_repo: AsyncMock,
        mock_party_membership_repo: AsyncMock,
    ) -> None:
        """political_party_id=NULLのみの政治家はスキップされる."""
        mock_election_member_repo.get_all_with_election_date.return_value = [
            (
                _make_member(politician_id=1, political_party_id=None, election_id=1),
                date(2012, 12, 16),
            ),
            (
                _make_member(politician_id=1, political_party_id=None, election_id=2),
                date(2017, 10, 22),
            ),
        ]
        mock_party_membership_repo.get_all.return_value = []

        result = await usecase.execute(RebuildPartyMembershipInputDto(dry_run=False))

        assert result.total_politicians == 1
        assert result.skipped_no_party == 1
        assert result.created_new_records == 0
        mock_party_membership_repo.create.assert_not_called()

    @pytest.mark.asyncio()
    async def test_dry_run_no_db_writes(
        self,
        usecase: RebuildPartyMembershipHistoryUseCase,
        mock_election_member_repo: AsyncMock,
        mock_party_membership_repo: AsyncMock,
    ) -> None:
        """dry_run=Trueの場合、DBへの書き込みが行われない."""
        mock_election_member_repo.get_all_with_election_date.return_value = [
            (
                _make_member(politician_id=1, political_party_id=10, election_id=1),
                date(2012, 12, 16),
            ),
            (
                _make_member(politician_id=1, political_party_id=20, election_id=2),
                date(2017, 10, 22),
            ),
        ]

        result = await usecase.execute(RebuildPartyMembershipInputDto(dry_run=True))

        assert result.dry_run is True
        assert result.created_new_records == 2
        assert result.deleted_old_records == 0
        # dry_runではget_all, delete, createは呼ばれない
        mock_party_membership_repo.get_all.assert_not_called()
        mock_party_membership_repo.delete.assert_not_called()
        mock_party_membership_repo.create.assert_not_called()

    @pytest.mark.asyncio()
    async def test_mixed_party_and_independent(
        self,
        usecase: RebuildPartyMembershipHistoryUseCase,
        mock_election_member_repo: AsyncMock,
        mock_party_membership_repo: AsyncMock,
    ) -> None:
        """政党X→無所属→政党Yの場合、無所属をスキップして2レコード作成."""
        date1 = date(2009, 8, 30)
        date2 = date(2012, 12, 16)  # 無所属
        date3 = date(2017, 10, 22)
        mock_election_member_repo.get_all_with_election_date.return_value = [
            (
                _make_member(politician_id=1, political_party_id=10, election_id=1),
                date1,
            ),
            (
                _make_member(politician_id=1, political_party_id=None, election_id=2),
                date2,
            ),
            (
                _make_member(politician_id=1, political_party_id=20, election_id=3),
                date3,
            ),
        ]
        mock_party_membership_repo.get_all.return_value = []

        result = await usecase.execute(RebuildPartyMembershipInputDto(dry_run=False))

        assert result.total_politicians == 1
        assert result.politicians_with_party_change == 1
        assert result.created_new_records == 2

        calls = mock_party_membership_repo.create.call_args_list
        first: PartyMembershipHistory = calls[0][0][0]
        assert first.political_party_id == 10
        assert first.start_date == date1
        # 無所属期間をスキップして次の政党出馬日の前日がend_date
        assert first.end_date == date3 - timedelta(days=1)

        second: PartyMembershipHistory = calls[1][0][0]
        assert second.political_party_id == 20
        assert second.start_date == date3
        assert second.end_date is None
