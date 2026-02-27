"""選挙当選者→ConferenceMember一括生成ユースケースのテスト."""

from datetime import date, timedelta
from unittest.mock import AsyncMock

import pytest

from src.application.dtos.conference_member_population_dto import (
    PopulateConferenceMembersInputDto,
)
from src.application.usecases.populate_conference_members_usecase import (
    PopulateConferenceMembersUseCase,
)
from src.domain.entities.conference import Conference
from src.domain.entities.conference_member import ConferenceMember
from src.domain.entities.election import Election
from src.domain.entities.election_member import ElectionMember
from src.domain.entities.politician import Politician
from src.domain.repositories.conference_member_repository import (
    ConferenceMemberRepository,
)
from src.domain.repositories.conference_repository import ConferenceRepository
from src.domain.repositories.election_member_repository import ElectionMemberRepository
from src.domain.repositories.election_repository import ElectionRepository
from src.domain.repositories.politician_repository import PoliticianRepository


ELECTION_DATE_49 = date(2021, 10, 31)
ELECTION_DATE_50 = date(2024, 10, 27)

# 参議院選挙日
SANGIIN_DATE_21 = date(2007, 7, 29)
SANGIIN_DATE_22 = date(2010, 7, 11)
SANGIIN_DATE_23 = date(2013, 7, 21)
SANGIIN_DATE_24 = date(2016, 7, 10)
SANGIIN_DATE_25 = date(2019, 7, 21)
SANGIIN_DATE_26 = date(2022, 7, 10)
SANGIIN_DATE_27 = date(2025, 7, 6)


class TestPopulateConferenceMembersUseCase:
    """ConferenceMember一括生成ユースケースのテスト."""

    @pytest.fixture()
    def mock_repos(self) -> dict[str, AsyncMock]:
        return {
            "election": AsyncMock(spec=ElectionRepository),
            "election_member": AsyncMock(spec=ElectionMemberRepository),
            "conference": AsyncMock(spec=ConferenceRepository),
            "conference_member": AsyncMock(spec=ConferenceMemberRepository),
            "politician": AsyncMock(spec=PoliticianRepository),
        }

    @pytest.fixture()
    def use_case(
        self, mock_repos: dict[str, AsyncMock]
    ) -> PopulateConferenceMembersUseCase:
        return PopulateConferenceMembersUseCase(
            election_repository=mock_repos["election"],
            election_member_repository=mock_repos["election_member"],
            conference_repository=mock_repos["conference"],
            conference_member_repository=mock_repos["conference_member"],
            politician_repository=mock_repos["politician"],
        )

    @pytest.fixture()
    def election_49(self) -> Election:
        return Election(
            governing_body_id=1,
            term_number=49,
            election_date=ELECTION_DATE_49,
            election_type="衆議院議員総選挙",
            id=1,
        )

    @pytest.fixture()
    def election_50(self) -> Election:
        return Election(
            governing_body_id=1,
            term_number=50,
            election_date=ELECTION_DATE_50,
            election_type="衆議院議員総選挙",
            id=2,
        )

    @pytest.fixture()
    def conference(self) -> Conference:
        return Conference(
            name="衆議院本会議",
            governing_body_id=1,
            id=10,
        )

    def _setup_basic_mocks(
        self,
        mock_repos: dict[str, AsyncMock],
        election: Election,
        conference: Conference,
        all_elections: list[Election] | None = None,
    ) -> None:
        """共通モック設定."""
        mock_repos["election"].get_by_governing_body_and_term.return_value = election
        mock_repos[
            "conference"
        ].get_by_name_and_governing_body.return_value = conference
        if all_elections is None:
            all_elections = [election]
        mock_repos["election"].get_by_governing_body.return_value = all_elections

    async def test_normal_elected_members_become_conference_members(
        self,
        use_case: PopulateConferenceMembersUseCase,
        mock_repos: dict[str, AsyncMock],
        election_50: Election,
        conference: Conference,
    ) -> None:
        """正常系: 当選者がConferenceMemberに変換される."""
        self._setup_basic_mocks(mock_repos, election_50, conference)
        mock_repos["election_member"].get_by_election_id.return_value = [
            ElectionMember(election_id=2, politician_id=1, result="当選", id=1),
            ElectionMember(election_id=2, politician_id=2, result="比例当選", id=2),
        ]
        mock_repos["politician"].get_by_ids.return_value = [
            Politician(name="議員太郎", prefecture="東京都", district="", id=1),
            Politician(name="議員花子", prefecture="大阪府", district="", id=2),
        ]
        mock_repos["conference_member"].get_by_conference.return_value = []
        mock_repos["conference_member"].upsert.return_value = ConferenceMember(
            politician_id=1,
            conference_id=10,
            start_date=ELECTION_DATE_50,
            id=1,
        )

        input_dto = PopulateConferenceMembersInputDto(term_number=50)
        result = await use_case.execute(input_dto)

        assert result.total_elected == 2
        assert result.created_count == 2
        assert result.already_existed_count == 0
        assert result.errors == 0
        assert mock_repos["conference_member"].upsert.call_count == 2

        # upsertに渡された引数の中身を検証
        calls = mock_repos["conference_member"].upsert.call_args_list
        assert calls[0].kwargs["politician_id"] == 1
        assert calls[0].kwargs["conference_id"] == 10
        assert calls[0].kwargs["start_date"] == ELECTION_DATE_50
        assert calls[1].kwargs["politician_id"] == 2
        assert calls[1].kwargs["conference_id"] == 10

        # populated_membersの中身を検証
        assert len(result.populated_members) == 2
        assert result.populated_members[0].politician_name == "議員太郎"
        assert result.populated_members[0].was_existing is False
        assert result.populated_members[1].politician_name == "議員花子"

    async def test_idempotency_no_duplicates(
        self,
        use_case: PopulateConferenceMembersUseCase,
        mock_repos: dict[str, AsyncMock],
        election_50: Election,
        conference: Conference,
    ) -> None:
        """冪等性: 既存メンバーは重複作成されない."""
        self._setup_basic_mocks(mock_repos, election_50, conference)
        mock_repos["election_member"].get_by_election_id.return_value = [
            ElectionMember(election_id=2, politician_id=1, result="当選", id=1),
        ]
        mock_repos["politician"].get_by_ids.return_value = [
            Politician(name="議員太郎", prefecture="東京都", district="", id=1),
        ]
        # 既に存在するメンバー
        mock_repos["conference_member"].get_by_conference.return_value = [
            ConferenceMember(
                politician_id=1,
                conference_id=10,
                start_date=ELECTION_DATE_50,
                id=100,
            ),
        ]

        input_dto = PopulateConferenceMembersInputDto(term_number=50)
        result = await use_case.execute(input_dto)

        assert result.created_count == 0
        assert result.already_existed_count == 1
        mock_repos["conference_member"].upsert.assert_not_called()

    async def test_end_date_calculated_from_next_election(
        self,
        use_case: PopulateConferenceMembersUseCase,
        mock_repos: dict[str, AsyncMock],
        election_49: Election,
        election_50: Election,
        conference: Conference,
    ) -> None:
        """end_date計算: 次回選挙日-1が設定される."""
        self._setup_basic_mocks(
            mock_repos,
            election_49,
            conference,
            all_elections=[election_49, election_50],
        )
        mock_repos["election_member"].get_by_election_id.return_value = [
            ElectionMember(election_id=1, politician_id=1, result="当選", id=1),
        ]
        mock_repos["politician"].get_by_ids.return_value = [
            Politician(name="議員太郎", prefecture="東京都", district="", id=1),
        ]
        mock_repos["conference_member"].get_by_conference.return_value = []
        mock_repos["conference_member"].upsert.return_value = ConferenceMember(
            politician_id=1,
            conference_id=10,
            start_date=ELECTION_DATE_49,
            end_date=ELECTION_DATE_50 - timedelta(days=1),
            id=1,
        )

        input_dto = PopulateConferenceMembersInputDto(term_number=49)
        result = await use_case.execute(input_dto)

        assert result.created_count == 1
        # upsertにend_date=次回選挙日-1が渡されている
        call_kwargs = mock_repos["conference_member"].upsert.call_args
        assert call_kwargs.kwargs["end_date"] == ELECTION_DATE_50 - timedelta(days=1)
        # populated_membersにもend_dateが設定
        assert result.populated_members[0].end_date == ELECTION_DATE_50 - timedelta(
            days=1
        )

    async def test_latest_election_end_date_is_none(
        self,
        use_case: PopulateConferenceMembersUseCase,
        mock_repos: dict[str, AsyncMock],
        election_49: Election,
        election_50: Election,
        conference: Conference,
    ) -> None:
        """最新選挙: end_date=None."""
        self._setup_basic_mocks(
            mock_repos,
            election_50,
            conference,
            all_elections=[election_49, election_50],
        )
        mock_repos["election_member"].get_by_election_id.return_value = [
            ElectionMember(election_id=2, politician_id=1, result="当選", id=1),
        ]
        mock_repos["politician"].get_by_ids.return_value = [
            Politician(name="議員太郎", prefecture="東京都", district="", id=1),
        ]
        mock_repos["conference_member"].get_by_conference.return_value = []
        mock_repos["conference_member"].upsert.return_value = ConferenceMember(
            politician_id=1,
            conference_id=10,
            start_date=ELECTION_DATE_50,
            id=1,
        )

        input_dto = PopulateConferenceMembersInputDto(term_number=50)
        result = await use_case.execute(input_dto)

        assert result.created_count == 1
        call_kwargs = mock_repos["conference_member"].upsert.call_args
        assert call_kwargs.kwargs["end_date"] is None
        assert result.populated_members[0].end_date is None

    async def test_election_not_found(
        self,
        use_case: PopulateConferenceMembersUseCase,
        mock_repos: dict[str, AsyncMock],
    ) -> None:
        """選挙未発見: エラーメッセージ返却."""
        mock_repos["election"].get_by_governing_body_and_term.return_value = None

        input_dto = PopulateConferenceMembersInputDto(term_number=99)
        result = await use_case.execute(input_dto)

        assert result.errors == 1
        assert "第99回の選挙が見つかりません" in result.error_details

    async def test_conference_not_found(
        self,
        use_case: PopulateConferenceMembersUseCase,
        mock_repos: dict[str, AsyncMock],
        election_50: Election,
    ) -> None:
        """会議体未発見: エラーメッセージ返却."""
        mock_repos["election"].get_by_governing_body_and_term.return_value = election_50
        mock_repos["election_member"].get_by_election_id.return_value = [
            ElectionMember(election_id=2, politician_id=1, result="当選", id=1),
        ]
        mock_repos["conference"].get_by_name_and_governing_body.return_value = None

        input_dto = PopulateConferenceMembersInputDto(term_number=50)
        result = await use_case.execute(input_dto)

        assert result.errors == 1
        assert "会議体'衆議院本会議'が見つかりません" in result.error_details

    async def test_no_elected_members(
        self,
        use_case: PopulateConferenceMembersUseCase,
        mock_repos: dict[str, AsyncMock],
        election_50: Election,
    ) -> None:
        """当選者0件: 正常終了."""
        mock_repos["election"].get_by_governing_body_and_term.return_value = election_50
        mock_repos["election_member"].get_by_election_id.return_value = [
            ElectionMember(election_id=2, politician_id=1, result="落選", id=1),
        ]

        input_dto = PopulateConferenceMembersInputDto(term_number=50)
        result = await use_case.execute(input_dto)

        assert result.total_elected == 0
        assert result.created_count == 0
        assert result.errors == 0

    async def test_dry_run_no_upsert_called(
        self,
        use_case: PopulateConferenceMembersUseCase,
        mock_repos: dict[str, AsyncMock],
        election_50: Election,
        conference: Conference,
    ) -> None:
        """dry_run: upsertが呼ばれない."""
        self._setup_basic_mocks(mock_repos, election_50, conference)
        mock_repos["election_member"].get_by_election_id.return_value = [
            ElectionMember(election_id=2, politician_id=1, result="当選", id=1),
        ]
        mock_repos["politician"].get_by_ids.return_value = [
            Politician(name="議員太郎", prefecture="東京都", district="", id=1),
        ]
        mock_repos["conference_member"].get_by_conference.return_value = []

        input_dto = PopulateConferenceMembersInputDto(term_number=50, dry_run=True)
        result = await use_case.execute(input_dto)

        assert result.created_count == 1
        mock_repos["conference_member"].upsert.assert_not_called()

    async def test_filters_only_same_chamber_elections_for_end_date(
        self,
        use_case: PopulateConferenceMembersUseCase,
        mock_repos: dict[str, AsyncMock],
        election_50: Election,
        conference: Conference,
    ) -> None:
        """end_date算出で同一院の選挙のみフィルタされる."""
        # 参議院選挙（異なる院）が混在しても無視される
        sangiin_election = Election(
            governing_body_id=1,
            term_number=26,
            election_date=date(2022, 7, 10),
            election_type="参議院議員通常選挙",
            id=99,
        )
        self._setup_basic_mocks(
            mock_repos,
            election_50,
            conference,
            all_elections=[election_50, sangiin_election],
        )
        mock_repos["election_member"].get_by_election_id.return_value = [
            ElectionMember(election_id=2, politician_id=1, result="当選", id=1),
        ]
        mock_repos["politician"].get_by_ids.return_value = [
            Politician(name="議員太郎", prefecture="東京都", district="", id=1),
        ]
        mock_repos["conference_member"].get_by_conference.return_value = []
        mock_repos["conference_member"].upsert.return_value = ConferenceMember(
            politician_id=1,
            conference_id=10,
            start_date=ELECTION_DATE_50,
            id=1,
        )

        input_dto = PopulateConferenceMembersInputDto(term_number=50)
        result = await use_case.execute(input_dto)

        # 衆議院の最新選挙なのでend_date=None
        call_kwargs = mock_repos["conference_member"].upsert.call_args
        assert call_kwargs.kwargs["end_date"] is None
        assert result.populated_members[0].end_date is None

    async def test_politician_not_found_uses_fallback_name(
        self,
        use_case: PopulateConferenceMembersUseCase,
        mock_repos: dict[str, AsyncMock],
        election_50: Election,
        conference: Conference,
    ) -> None:
        """政治家情報が取得できない場合、IDをフォールバック名として使用する."""
        self._setup_basic_mocks(mock_repos, election_50, conference)
        mock_repos["election_member"].get_by_election_id.return_value = [
            ElectionMember(election_id=2, politician_id=999, result="当選", id=1),
        ]
        mock_repos["politician"].get_by_ids.return_value = []
        mock_repos["conference_member"].get_by_conference.return_value = []
        mock_repos["conference_member"].upsert.return_value = ConferenceMember(
            politician_id=999,
            conference_id=10,
            start_date=ELECTION_DATE_50,
            id=1,
        )

        input_dto = PopulateConferenceMembersInputDto(term_number=50)
        result = await use_case.execute(input_dto)

        assert result.populated_members[0].politician_name == "ID:999"
        assert result.created_count == 1

    @pytest.mark.parametrize(
        "result_value",
        ["当選", "繰上当選", "無投票当選", "比例当選", "比例復活"],
    )
    async def test_all_elected_result_types_are_recognized(
        self,
        use_case: PopulateConferenceMembersUseCase,
        mock_repos: dict[str, AsyncMock],
        election_50: Election,
        conference: Conference,
        result_value: str,
    ) -> None:
        """全当選種別がConferenceMemberに変換される."""
        self._setup_basic_mocks(mock_repos, election_50, conference)
        mock_repos["election_member"].get_by_election_id.return_value = [
            ElectionMember(election_id=2, politician_id=1, result=result_value, id=1),
        ]
        mock_repos["politician"].get_by_ids.return_value = [
            Politician(name="議員太郎", prefecture="東京都", district="", id=1),
        ]
        mock_repos["conference_member"].get_by_conference.return_value = []
        mock_repos["conference_member"].upsert.return_value = ConferenceMember(
            politician_id=1,
            conference_id=10,
            start_date=ELECTION_DATE_50,
            id=1,
        )

        input_dto = PopulateConferenceMembersInputDto(term_number=50)
        result = await use_case.execute(input_dto)

        assert result.total_elected == 1
        assert result.created_count == 1

    async def test_same_politician_different_terms_not_skipped(
        self,
        use_case: PopulateConferenceMembersUseCase,
        mock_repos: dict[str, AsyncMock],
        election_49: Election,
        election_50: Election,
        conference: Conference,
    ) -> None:
        """同一政治家が別回次で当選済みでも、異なるstart_dateなら新規作成される."""
        self._setup_basic_mocks(
            mock_repos,
            election_49,
            conference,
            all_elections=[election_49, election_50],
        )
        mock_repos["election_member"].get_by_election_id.return_value = [
            ElectionMember(election_id=1, politician_id=1, result="当選", id=1),
        ]
        mock_repos["politician"].get_by_ids.return_value = [
            Politician(name="議員太郎", prefecture="東京都", district="", id=1),
        ]
        # 第50回で既に登録済みのメンバー（start_dateが異なる）
        mock_repos["conference_member"].get_by_conference.return_value = [
            ConferenceMember(
                politician_id=1,
                conference_id=10,
                start_date=ELECTION_DATE_50,
                id=100,
            ),
        ]
        mock_repos["conference_member"].upsert.return_value = ConferenceMember(
            politician_id=1,
            conference_id=10,
            start_date=ELECTION_DATE_49,
            id=101,
        )

        input_dto = PopulateConferenceMembersInputDto(term_number=49)
        result = await use_case.execute(input_dto)

        # start_dateが異なるので新規作成される（既存扱いにならない）
        assert result.created_count == 1
        assert result.already_existed_count == 0
        mock_repos["conference_member"].upsert.assert_called_once()


class TestSangiinHalfRenewal:
    """参議院半数改選のend_date計算テスト."""

    @pytest.fixture()
    def mock_repos(self) -> dict[str, AsyncMock]:
        return {
            "election": AsyncMock(spec=ElectionRepository),
            "election_member": AsyncMock(spec=ElectionMemberRepository),
            "conference": AsyncMock(spec=ConferenceRepository),
            "conference_member": AsyncMock(spec=ConferenceMemberRepository),
            "politician": AsyncMock(spec=PoliticianRepository),
        }

    @pytest.fixture()
    def use_case(
        self, mock_repos: dict[str, AsyncMock]
    ) -> PopulateConferenceMembersUseCase:
        return PopulateConferenceMembersUseCase(
            election_repository=mock_repos["election"],
            election_member_repository=mock_repos["election_member"],
            conference_repository=mock_repos["conference"],
            conference_member_repository=mock_repos["conference_member"],
            politician_repository=mock_repos["politician"],
        )

    @pytest.fixture()
    def sangiin_conference(self) -> Conference:
        return Conference(
            name="参議院本会議",
            governing_body_id=1,
            id=20,
        )

    @pytest.fixture()
    def sangiin_elections(self) -> list[Election]:
        return [
            Election(
                governing_body_id=1,
                term_number=21,
                election_date=SANGIIN_DATE_21,
                election_type="参議院議員通常選挙",
                id=21,
            ),
            Election(
                governing_body_id=1,
                term_number=22,
                election_date=SANGIIN_DATE_22,
                election_type="参議院議員通常選挙",
                id=22,
            ),
            Election(
                governing_body_id=1,
                term_number=23,
                election_date=SANGIIN_DATE_23,
                election_type="参議院議員通常選挙",
                id=23,
            ),
            Election(
                governing_body_id=1,
                term_number=24,
                election_date=SANGIIN_DATE_24,
                election_type="参議院議員通常選挙",
                id=24,
            ),
            Election(
                governing_body_id=1,
                term_number=25,
                election_date=SANGIIN_DATE_25,
                election_type="参議院議員通常選挙",
                id=25,
            ),
            Election(
                governing_body_id=1,
                term_number=26,
                election_date=SANGIIN_DATE_26,
                election_type="参議院議員通常選挙",
                id=26,
            ),
            Election(
                governing_body_id=1,
                term_number=27,
                election_date=SANGIIN_DATE_27,
                election_type="参議院議員通常選挙",
                id=27,
            ),
        ]

    def _setup_sangiin_mocks(
        self,
        mock_repos: dict[str, AsyncMock],
        target_election: Election,
        all_elections: list[Election],
        conference: Conference,
    ) -> None:
        mock_repos[
            "election"
        ].get_by_governing_body_and_term.return_value = target_election
        mock_repos[
            "conference"
        ].get_by_name_and_governing_body.return_value = conference
        mock_repos["election"].get_by_governing_body.return_value = all_elections
        mock_repos["election_member"].get_by_election_id.return_value = [
            ElectionMember(
                election_id=target_election.id,
                politician_id=1,
                result="当選",
                id=1,
            ),
        ]
        mock_repos["politician"].get_by_ids.return_value = [
            Politician(name="参議員太郎", prefecture="東京都", district="", id=1),
        ]
        mock_repos["conference_member"].get_by_conference.return_value = []
        mock_repos["conference_member"].upsert.return_value = ConferenceMember(
            politician_id=1,
            conference_id=conference.id,
            start_date=target_election.election_date,
            id=1,
        )

    async def test_sangiin_half_renewal_end_date_odd(
        self,
        use_case: PopulateConferenceMembersUseCase,
        mock_repos: dict[str, AsyncMock],
        sangiin_elections: list[Election],
        sangiin_conference: Conference,
    ) -> None:
        """参議院奇数回（第25回）→ 同パリティの次回（第27回）前日がend_date."""
        election_25 = sangiin_elections[4]  # term_number=25
        self._setup_sangiin_mocks(
            mock_repos, election_25, sangiin_elections, sangiin_conference
        )

        input_dto = PopulateConferenceMembersInputDto(
            term_number=25,
            conference_name="参議院本会議",
        )
        result = await use_case.execute(input_dto)

        call_kwargs = mock_repos["conference_member"].upsert.call_args
        expected_end_date = SANGIIN_DATE_27 - timedelta(days=1)
        assert call_kwargs.kwargs["end_date"] == expected_end_date
        assert result.populated_members[0].end_date == expected_end_date

    async def test_sangiin_half_renewal_end_date_even_no_next(
        self,
        use_case: PopulateConferenceMembersUseCase,
        mock_repos: dict[str, AsyncMock],
        sangiin_elections: list[Election],
        sangiin_conference: Conference,
    ) -> None:
        """参議院偶数回（第26回）→ 次の偶数回（第28回）未登録のためNone."""
        election_26 = sangiin_elections[5]  # term_number=26
        self._setup_sangiin_mocks(
            mock_repos, election_26, sangiin_elections, sangiin_conference
        )

        input_dto = PopulateConferenceMembersInputDto(
            term_number=26,
            conference_name="参議院本会議",
        )
        result = await use_case.execute(input_dto)

        call_kwargs = mock_repos["conference_member"].upsert.call_args
        assert call_kwargs.kwargs["end_date"] is None
        assert result.populated_members[0].end_date is None

    async def test_sangiin_half_renewal_end_date_even_with_next(
        self,
        use_case: PopulateConferenceMembersUseCase,
        mock_repos: dict[str, AsyncMock],
        sangiin_elections: list[Election],
        sangiin_conference: Conference,
    ) -> None:
        """参議院偶数回（第22回）→ 次の偶数回（第24回）前日がend_date."""
        election_22 = sangiin_elections[1]  # term_number=22
        self._setup_sangiin_mocks(
            mock_repos, election_22, sangiin_elections, sangiin_conference
        )

        input_dto = PopulateConferenceMembersInputDto(
            term_number=22,
            conference_name="参議院本会議",
        )
        result = await use_case.execute(input_dto)

        call_kwargs = mock_repos["conference_member"].upsert.call_args
        expected_end_date = SANGIIN_DATE_24 - timedelta(days=1)
        assert call_kwargs.kwargs["end_date"] == expected_end_date
        assert result.populated_members[0].end_date == expected_end_date

    async def test_shugiin_end_date_unchanged_with_sangiin_present(
        self,
        use_case: PopulateConferenceMembersUseCase,
        mock_repos: dict[str, AsyncMock],
        sangiin_elections: list[Election],
    ) -> None:
        """衆議院の挙動回帰テスト: 参議院選挙が混在していても衆議院は従来通り."""
        election_49 = Election(
            governing_body_id=1,
            term_number=49,
            election_date=ELECTION_DATE_49,
            election_type="衆議院議員総選挙",
            id=49,
        )
        election_50 = Election(
            governing_body_id=1,
            term_number=50,
            election_date=ELECTION_DATE_50,
            election_type="衆議院議員総選挙",
            id=50,
        )
        conference = Conference(name="衆議院本会議", governing_body_id=1, id=10)

        all_elections = [election_49, election_50, *sangiin_elections]
        mock_repos["election"].get_by_governing_body_and_term.return_value = election_49
        mock_repos[
            "conference"
        ].get_by_name_and_governing_body.return_value = conference
        mock_repos["election"].get_by_governing_body.return_value = all_elections
        mock_repos["election_member"].get_by_election_id.return_value = [
            ElectionMember(election_id=49, politician_id=1, result="当選", id=1),
        ]
        mock_repos["politician"].get_by_ids.return_value = [
            Politician(name="議員太郎", prefecture="東京都", district="", id=1),
        ]
        mock_repos["conference_member"].get_by_conference.return_value = []
        mock_repos["conference_member"].upsert.return_value = ConferenceMember(
            politician_id=1,
            conference_id=10,
            start_date=ELECTION_DATE_49,
            id=1,
        )

        input_dto = PopulateConferenceMembersInputDto(term_number=49)
        result = await use_case.execute(input_dto)

        call_kwargs = mock_repos["conference_member"].upsert.call_args
        expected_end_date = ELECTION_DATE_50 - timedelta(days=1)
        assert call_kwargs.kwargs["end_date"] == expected_end_date
        assert result.populated_members[0].end_date == expected_end_date
