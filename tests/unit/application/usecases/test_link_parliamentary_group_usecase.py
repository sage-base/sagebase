"""会派自動紐付けユースケースのテスト."""

from datetime import date
from unittest.mock import AsyncMock

import pytest

from src.application.dtos.parliamentary_group_linkage_dto import (
    LinkParliamentaryGroupInputDto,
)
from src.application.usecases.link_parliamentary_group_usecase import (
    LinkParliamentaryGroupUseCase,
)
from src.domain.entities.election import Election
from src.domain.entities.election_member import ElectionMember
from src.domain.entities.parliamentary_group import ParliamentaryGroup
from src.domain.entities.parliamentary_group_membership import (
    ParliamentaryGroupMembership,
)
from src.domain.entities.party_membership_history import PartyMembershipHistory
from src.domain.entities.politician import Politician
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


ELECTION_DATE = date(2024, 10, 27)


class TestLinkParliamentaryGroupUseCase:
    """会派自動紐付けユースケースのテスト."""

    @pytest.fixture()
    def mock_repos(self) -> dict[str, AsyncMock]:
        return {
            "election": AsyncMock(spec=ElectionRepository),
            "election_member": AsyncMock(spec=ElectionMemberRepository),
            "politician": AsyncMock(spec=PoliticianRepository),
            "group": AsyncMock(spec=ParliamentaryGroupRepository),
            "membership": AsyncMock(spec=ParliamentaryGroupMembershipRepository),
            "party_history": AsyncMock(spec=PartyMembershipHistoryRepository),
        }

    @pytest.fixture()
    def use_case(
        self, mock_repos: dict[str, AsyncMock]
    ) -> LinkParliamentaryGroupUseCase:
        return LinkParliamentaryGroupUseCase(
            election_repository=mock_repos["election"],
            election_member_repository=mock_repos["election_member"],
            politician_repository=mock_repos["politician"],
            parliamentary_group_repository=mock_repos["group"],
            parliamentary_group_membership_repository=mock_repos["membership"],
            party_membership_history_repository=mock_repos["party_history"],
        )

    @pytest.fixture()
    def election(self) -> Election:
        return Election(
            governing_body_id=1,
            term_number=50,
            election_date=ELECTION_DATE,
            election_type="衆議院議員総選挙",
            id=1,
        )

    @pytest.fixture()
    def ldp_group(self) -> ParliamentaryGroup:
        return ParliamentaryGroup(
            name="自由民主党・無所属の会",
            governing_body_id=1,
            political_party_id=10,
            is_active=True,
            id=100,
        )

    @pytest.fixture()
    def cdp_group(self) -> ParliamentaryGroup:
        return ParliamentaryGroup(
            name="立憲民主党・無所属",
            governing_body_id=1,
            political_party_id=20,
            is_active=True,
            id=200,
        )

    def _setup_election(
        self,
        mock_repos: dict[str, AsyncMock],
        election: Election,
    ) -> None:
        mock_repos["election"].get_by_governing_body_and_term.return_value = election

    async def test_election_not_found(
        self,
        use_case: LinkParliamentaryGroupUseCase,
        mock_repos: dict[str, AsyncMock],
    ) -> None:
        """選挙が見つからない場合エラーを返す."""
        mock_repos["election"].get_by_governing_body_and_term.return_value = None

        input_dto = LinkParliamentaryGroupInputDto(term_number=99)
        result = await use_case.execute(input_dto)

        assert result.errors == 1
        assert "第99回の選挙が見つかりません" in result.error_details

    async def test_no_elected_members(
        self,
        use_case: LinkParliamentaryGroupUseCase,
        mock_repos: dict[str, AsyncMock],
        election: Election,
    ) -> None:
        """当選者が0件の場合."""
        self._setup_election(mock_repos, election)
        mock_repos["election_member"].get_by_election_id.return_value = [
            ElectionMember(election_id=1, politician_id=1, result="落選", id=1),
        ]

        input_dto = LinkParliamentaryGroupInputDto(term_number=50)
        result = await use_case.execute(input_dto)

        assert result.total_elected == 0
        assert result.linked_count == 0

    async def test_skip_no_party_id(
        self,
        use_case: LinkParliamentaryGroupUseCase,
        mock_repos: dict[str, AsyncMock],
        election: Election,
        ldp_group: ParliamentaryGroup,
    ) -> None:
        """政党所属履歴なしでスキップ."""
        self._setup_election(mock_repos, election)
        mock_repos["election_member"].get_by_election_id.return_value = [
            ElectionMember(election_id=1, politician_id=1, result="当選", id=1),
        ]
        mock_repos["politician"].get_by_ids.return_value = [
            Politician(name="無所属太郎", prefecture="東京都", district="", id=1),
        ]
        # 履歴なし
        mock_repos["party_history"].get_current_by_politicians.return_value = {}
        mock_repos["group"].get_by_governing_body_id.return_value = [ldp_group]
        mock_repos["membership"].get_active_by_group.return_value = []

        input_dto = LinkParliamentaryGroupInputDto(term_number=50)
        result = await use_case.execute(input_dto)

        assert result.skipped_no_party == 1
        assert result.linked_count == 0
        assert result.skipped_members[0].reason == "政党所属履歴なし"

    async def test_skip_no_matching_group(
        self,
        use_case: LinkParliamentaryGroupUseCase,
        mock_repos: dict[str, AsyncMock],
        election: Election,
        ldp_group: ParliamentaryGroup,
    ) -> None:
        """対応する会派がない場合スキップ."""
        self._setup_election(mock_repos, election)
        mock_repos["election_member"].get_by_election_id.return_value = [
            ElectionMember(election_id=1, politician_id=1, result="当選", id=1),
        ]
        mock_repos["politician"].get_by_ids.return_value = [
            Politician(
                name="新党太郎",
                prefecture="東京都",
                district="",
                id=1,
            ),
        ]
        # 政党99はldp_group(10)に合致しない
        mock_repos["party_history"].get_current_by_politicians.return_value = {
            1: PartyMembershipHistory(
                politician_id=1,
                political_party_id=99,
                start_date=date(2020, 1, 1),
                end_date=None,
            ),
        }
        mock_repos["group"].get_by_governing_body_id.return_value = [ldp_group]
        mock_repos["membership"].get_active_by_group.return_value = []

        input_dto = LinkParliamentaryGroupInputDto(term_number=50)
        result = await use_case.execute(input_dto)

        assert result.skipped_no_group == 1
        assert result.skipped_members[0].reason == "対応する会派なし"

    async def test_skip_multiple_groups(
        self,
        use_case: LinkParliamentaryGroupUseCase,
        mock_repos: dict[str, AsyncMock],
        election: Election,
    ) -> None:
        """複数会派が該当する場合スキップ."""
        self._setup_election(mock_repos, election)
        mock_repos["election_member"].get_by_election_id.return_value = [
            ElectionMember(election_id=1, politician_id=1, result="当選", id=1),
        ]
        mock_repos["politician"].get_by_ids.return_value = [
            Politician(
                name="維新太郎",
                prefecture="大阪府",
                district="",
                id=1,
            ),
        ]
        group_a = ParliamentaryGroup(
            name="日本維新の会A",
            governing_body_id=1,
            political_party_id=30,
            is_active=True,
            id=301,
        )
        group_b = ParliamentaryGroup(
            name="日本維新の会B",
            governing_body_id=1,
            political_party_id=30,
            is_active=True,
            id=302,
        )
        # 政党30は両方のグループに合致
        mock_repos["party_history"].get_current_by_politicians.return_value = {
            1: PartyMembershipHistory(
                politician_id=1,
                political_party_id=30,
                start_date=date(2020, 1, 1),
                end_date=None,
            ),
        }
        mock_repos["group"].get_by_governing_body_id.return_value = [group_a, group_b]
        mock_repos["membership"].get_active_by_group.return_value = []

        input_dto = LinkParliamentaryGroupInputDto(term_number=50)
        result = await use_case.execute(input_dto)

        assert result.skipped_multiple_groups == 1
        assert "複数会派" in result.skipped_members[0].reason

    async def test_single_match_creates_membership(
        self,
        use_case: LinkParliamentaryGroupUseCase,
        mock_repos: dict[str, AsyncMock],
        election: Election,
        ldp_group: ParliamentaryGroup,
    ) -> None:
        """1:1マッチで正常にメンバーシップを作成."""
        self._setup_election(mock_repos, election)
        mock_repos["election_member"].get_by_election_id.return_value = [
            ElectionMember(election_id=1, politician_id=1, result="当選", id=1),
        ]
        mock_repos["politician"].get_by_ids.return_value = [
            Politician(
                name="自民太郎",
                prefecture="東京都",
                district="",
                id=1,
            ),
        ]
        mock_repos["party_history"].get_current_by_politicians.return_value = {
            1: PartyMembershipHistory(
                politician_id=1,
                political_party_id=10,
                start_date=date(2020, 1, 1),
                end_date=None,
            ),
        }
        mock_repos["group"].get_by_governing_body_id.return_value = [ldp_group]
        mock_repos["membership"].get_active_by_group.return_value = []
        mock_repos[
            "membership"
        ].create_membership.return_value = ParliamentaryGroupMembership(
            politician_id=1,
            parliamentary_group_id=100,
            start_date=ELECTION_DATE,
            id=1,
        )

        input_dto = LinkParliamentaryGroupInputDto(term_number=50)
        result = await use_case.execute(input_dto)

        assert result.linked_count == 1
        assert result.already_existed_count == 0
        mock_repos["membership"].create_membership.assert_called_once_with(
            politician_id=1,
            group_id=100,
            start_date=ELECTION_DATE,
        )
        assert result.linked_members[0].politician_name == "自民太郎"
        assert (
            result.linked_members[0].parliamentary_group_name
            == "自由民主党・無所属の会"
        )

    async def test_already_existing_membership(
        self,
        use_case: LinkParliamentaryGroupUseCase,
        mock_repos: dict[str, AsyncMock],
        election: Election,
        ldp_group: ParliamentaryGroup,
    ) -> None:
        """既にメンバーシップが存在する場合、already_existed_countが増加."""
        self._setup_election(mock_repos, election)
        mock_repos["election_member"].get_by_election_id.return_value = [
            ElectionMember(election_id=1, politician_id=1, result="当選", id=1),
        ]
        mock_repos["politician"].get_by_ids.return_value = [
            Politician(
                name="自民太郎",
                prefecture="東京都",
                district="",
                id=1,
            ),
        ]
        mock_repos["party_history"].get_current_by_politicians.return_value = {
            1: PartyMembershipHistory(
                politician_id=1,
                political_party_id=10,
                start_date=date(2020, 1, 1),
                end_date=None,
            ),
        }
        mock_repos["group"].get_by_governing_body_id.return_value = [ldp_group]
        mock_repos["membership"].get_active_by_group.return_value = [
            ParliamentaryGroupMembership(
                politician_id=1,
                parliamentary_group_id=100,
                start_date=ELECTION_DATE,
                id=99,
            ),
        ]

        input_dto = LinkParliamentaryGroupInputDto(term_number=50)
        result = await use_case.execute(input_dto)

        assert result.already_existed_count == 1
        assert result.linked_count == 0
        assert result.linked_members[0].was_existing is True
        mock_repos["membership"].create_membership.assert_not_called()

    async def test_dry_run_no_writes(
        self,
        use_case: LinkParliamentaryGroupUseCase,
        mock_repos: dict[str, AsyncMock],
        election: Election,
        ldp_group: ParliamentaryGroup,
    ) -> None:
        """ドライランでDB書き込みが行われない."""
        self._setup_election(mock_repos, election)
        mock_repos["election_member"].get_by_election_id.return_value = [
            ElectionMember(election_id=1, politician_id=1, result="当選", id=1),
        ]
        mock_repos["politician"].get_by_ids.return_value = [
            Politician(
                name="自民太郎",
                prefecture="東京都",
                district="",
                id=1,
            ),
        ]
        mock_repos["party_history"].get_current_by_politicians.return_value = {
            1: PartyMembershipHistory(
                politician_id=1,
                political_party_id=10,
                start_date=date(2020, 1, 1),
                end_date=None,
            ),
        }
        mock_repos["group"].get_by_governing_body_id.return_value = [ldp_group]
        mock_repos["membership"].get_active_by_group.return_value = []

        input_dto = LinkParliamentaryGroupInputDto(term_number=50, dry_run=True)
        result = await use_case.execute(input_dto)

        assert result.linked_count == 1
        mock_repos["membership"].create_membership.assert_not_called()

    async def test_full_flow_mixed(
        self,
        use_case: LinkParliamentaryGroupUseCase,
        mock_repos: dict[str, AsyncMock],
        election: Election,
        ldp_group: ParliamentaryGroup,
        cdp_group: ParliamentaryGroup,
    ) -> None:
        """複合シナリオ: 紐付け成功 + 政党未設定スキップ + 会派なしスキップ."""
        self._setup_election(mock_repos, election)
        mock_repos["election_member"].get_by_election_id.return_value = [
            ElectionMember(election_id=1, politician_id=1, result="当選", id=1),
            ElectionMember(election_id=1, politician_id=2, result="当選", id=2),
            ElectionMember(election_id=1, politician_id=3, result="当選", id=3),
        ]
        mock_repos["politician"].get_by_ids.return_value = [
            Politician(
                name="自民太郎",
                prefecture="東京都",
                district="",
                id=1,
            ),
            Politician(
                name="無所属花子",
                prefecture="大阪府",
                district="",
                id=2,
            ),
            Politician(
                name="新党次郎",
                prefecture="北海道",
                district="",
                id=3,
            ),
        ]
        # 1=自民(10→紐付け成功), 2=履歴なし(スキップ), 3=新党(99→会派なしスキップ)
        mock_repos["party_history"].get_current_by_politicians.return_value = {
            1: PartyMembershipHistory(
                politician_id=1,
                political_party_id=10,
                start_date=date(2020, 1, 1),
                end_date=None,
            ),
            3: PartyMembershipHistory(
                politician_id=3,
                political_party_id=99,
                start_date=date(2020, 1, 1),
                end_date=None,
            ),
        }
        mock_repos["group"].get_by_governing_body_id.return_value = [
            ldp_group,
            cdp_group,
        ]
        mock_repos["membership"].get_active_by_group.return_value = []
        mock_repos[
            "membership"
        ].create_membership.return_value = ParliamentaryGroupMembership(
            politician_id=1,
            parliamentary_group_id=100,
            start_date=ELECTION_DATE,
            id=1,
        )

        input_dto = LinkParliamentaryGroupInputDto(term_number=50)
        result = await use_case.execute(input_dto)

        assert result.total_elected == 3
        assert result.linked_count == 1
        assert result.skipped_no_party == 1
        assert result.skipped_no_group == 1
        assert result.errors == 0

    async def test_politician_not_found(
        self,
        use_case: LinkParliamentaryGroupUseCase,
        mock_repos: dict[str, AsyncMock],
        election: Election,
        ldp_group: ParliamentaryGroup,
    ) -> None:
        """politician_idに対応する政治家が見つからない場合エラー."""
        self._setup_election(mock_repos, election)
        mock_repos["election_member"].get_by_election_id.return_value = [
            ElectionMember(election_id=1, politician_id=999, result="当選", id=1),
        ]
        mock_repos["politician"].get_by_ids.return_value = []
        mock_repos["party_history"].get_current_by_politicians.return_value = {}
        mock_repos["group"].get_by_governing_body_id.return_value = [ldp_group]
        mock_repos["membership"].get_active_by_group.return_value = []

        input_dto = LinkParliamentaryGroupInputDto(term_number=50)
        result = await use_case.execute(input_dto)

        assert result.errors == 1
        assert "politician_id=999が見つかりません" in result.error_details


class TestLinkParliamentaryGroupWithHistory:
    """履歴ベースの会派紐付けテスト."""

    @pytest.fixture()
    def mock_repos(self) -> dict[str, AsyncMock]:
        return {
            "election": AsyncMock(spec=ElectionRepository),
            "election_member": AsyncMock(spec=ElectionMemberRepository),
            "politician": AsyncMock(spec=PoliticianRepository),
            "group": AsyncMock(spec=ParliamentaryGroupRepository),
            "membership": AsyncMock(spec=ParliamentaryGroupMembershipRepository),
            "party_history": AsyncMock(spec=PartyMembershipHistoryRepository),
        }

    @pytest.fixture()
    def use_case_with_history(
        self, mock_repos: dict[str, AsyncMock]
    ) -> LinkParliamentaryGroupUseCase:
        return LinkParliamentaryGroupUseCase(
            election_repository=mock_repos["election"],
            election_member_repository=mock_repos["election_member"],
            politician_repository=mock_repos["politician"],
            parliamentary_group_repository=mock_repos["group"],
            parliamentary_group_membership_repository=mock_repos["membership"],
            party_membership_history_repository=mock_repos["party_history"],
        )

    @pytest.fixture()
    def election(self) -> Election:
        return Election(
            governing_body_id=1,
            term_number=50,
            election_date=ELECTION_DATE,
            election_type="衆議院議員総選挙",
            id=1,
        )

    @pytest.fixture()
    def ldp_group(self) -> ParliamentaryGroup:
        return ParliamentaryGroup(
            name="自由民主党・無所属の会",
            governing_body_id=1,
            political_party_id=10,
            is_active=True,
            id=100,
        )

    def _setup_election(
        self,
        mock_repos: dict[str, AsyncMock],
        election: Election,
    ) -> None:
        mock_repos["election"].get_by_governing_body_and_term.return_value = election

    async def test_uses_party_history_when_available(
        self,
        use_case_with_history: LinkParliamentaryGroupUseCase,
        mock_repos: dict[str, AsyncMock],
        election: Election,
        ldp_group: ParliamentaryGroup,
    ) -> None:
        """履歴ベースのparty_idで会派マッチング."""
        self._setup_election(mock_repos, election)
        mock_repos["election_member"].get_by_election_id.return_value = [
            ElectionMember(election_id=1, politician_id=1, result="当選", id=1),
        ]
        # 履歴のpolitical_party_id=10が使われる
        mock_repos["politician"].get_by_ids.return_value = [
            Politician(
                name="自民太郎",
                prefecture="東京都",
                district="",
                id=1,
            ),
        ]
        mock_repos["party_history"].get_current_by_politicians.return_value = {
            1: PartyMembershipHistory(
                politician_id=1,
                political_party_id=10,
                start_date=date(2024, 1, 1),
                id=1,
            ),
        }
        mock_repos["group"].get_by_governing_body_id.return_value = [ldp_group]
        mock_repos["membership"].get_active_by_group.return_value = []
        mock_repos[
            "membership"
        ].create_membership.return_value = ParliamentaryGroupMembership(
            politician_id=1,
            parliamentary_group_id=100,
            start_date=ELECTION_DATE,
            id=1,
        )

        input_dto = LinkParliamentaryGroupInputDto(term_number=50)
        result = await use_case_with_history.execute(input_dto)

        assert result.linked_count == 1
        assert (
            result.linked_members[0].parliamentary_group_name
            == "自由民主党・無所属の会"
        )

    async def test_history_different_party_than_snapshot(
        self,
        use_case_with_history: LinkParliamentaryGroupUseCase,
        mock_repos: dict[str, AsyncMock],
        election: Election,
        ldp_group: ParliamentaryGroup,
    ) -> None:
        """履歴値とスナップショット値が異なる場合に履歴値が使われる."""
        self._setup_election(mock_repos, election)
        mock_repos["election_member"].get_by_election_id.return_value = [
            ElectionMember(election_id=1, politician_id=1, result="当選", id=1),
        ]
        # 履歴のpolitical_party_id=999が使われる
        mock_repos["politician"].get_by_ids.return_value = [
            Politician(
                name="元自民太郎",
                prefecture="東京都",
                district="",
                id=1,
            ),
        ]
        mock_repos["party_history"].get_current_by_politicians.return_value = {
            1: PartyMembershipHistory(
                politician_id=1,
                political_party_id=999,
                start_date=date(2024, 1, 1),
                id=1,
            ),
        }
        mock_repos["group"].get_by_governing_body_id.return_value = [ldp_group]
        mock_repos["membership"].get_active_by_group.return_value = []

        input_dto = LinkParliamentaryGroupInputDto(term_number=50)
        result = await use_case_with_history.execute(input_dto)

        # 履歴のparty_id=999なので自民の会派にマッチしない
        assert result.skipped_no_group == 1
        assert result.linked_count == 0

    async def test_chamber_filter_passed_to_repository(
        self,
        use_case_with_history: LinkParliamentaryGroupUseCase,
        mock_repos: dict[str, AsyncMock],
        election: Election,
        ldp_group: ParliamentaryGroup,
    ) -> None:
        """chamber指定時にget_by_governing_body_idへchamberが正しく渡される."""
        self._setup_election(mock_repos, election)
        mock_repos["election_member"].get_by_election_id.return_value = [
            ElectionMember(election_id=1, politician_id=1, result="当選", id=1),
        ]
        mock_repos["politician"].get_by_ids.return_value = [
            Politician(
                name="自民太郎",
                prefecture="東京都",
                district="",
                id=1,
            ),
        ]
        mock_repos["party_history"].get_current_by_politicians.return_value = {
            1: PartyMembershipHistory(
                politician_id=1,
                political_party_id=10,
                start_date=date(2024, 1, 1),
                id=1,
            ),
        }
        mock_repos["group"].get_by_governing_body_id.return_value = [ldp_group]
        mock_repos["membership"].get_active_by_group.return_value = []
        mock_repos[
            "membership"
        ].create_membership.return_value = ParliamentaryGroupMembership(
            politician_id=1,
            parliamentary_group_id=100,
            start_date=ELECTION_DATE,
            id=1,
        )

        input_dto = LinkParliamentaryGroupInputDto(term_number=50, chamber="衆議院")
        await use_case_with_history.execute(input_dto)

        # chamberが正しくリポジトリに渡されていること
        mock_repos["group"].get_by_governing_body_id.assert_called_once_with(
            1, active_only=True, chamber="衆議院"
        )

    async def test_empty_chamber_passes_none_to_repository(
        self,
        use_case_with_history: LinkParliamentaryGroupUseCase,
        mock_repos: dict[str, AsyncMock],
        election: Election,
        ldp_group: ParliamentaryGroup,
    ) -> None:
        """chamber未指定時にNoneがget_by_governing_body_idへ渡される."""
        self._setup_election(mock_repos, election)
        mock_repos["election_member"].get_by_election_id.return_value = [
            ElectionMember(election_id=1, politician_id=1, result="当選", id=1),
        ]
        mock_repos["politician"].get_by_ids.return_value = [
            Politician(
                name="自民太郎",
                prefecture="東京都",
                district="",
                id=1,
            ),
        ]
        mock_repos["party_history"].get_current_by_politicians.return_value = {
            1: PartyMembershipHistory(
                politician_id=1,
                political_party_id=10,
                start_date=date(2024, 1, 1),
                id=1,
            ),
        }
        mock_repos["group"].get_by_governing_body_id.return_value = [ldp_group]
        mock_repos["membership"].get_active_by_group.return_value = []
        mock_repos[
            "membership"
        ].create_membership.return_value = ParliamentaryGroupMembership(
            politician_id=1,
            parliamentary_group_id=100,
            start_date=ELECTION_DATE,
            id=1,
        )

        input_dto = LinkParliamentaryGroupInputDto(term_number=50)
        await use_case_with_history.execute(input_dto)

        # chamber未指定なのでNoneが渡される
        mock_repos["group"].get_by_governing_body_id.assert_called_once_with(
            1, active_only=True, chamber=None
        )

    async def test_history_no_party_at_election_date(
        self,
        use_case_with_history: LinkParliamentaryGroupUseCase,
        mock_repos: dict[str, AsyncMock],
        election: Election,
        ldp_group: ParliamentaryGroup,
    ) -> None:
        """選挙日時点で履歴なし → 政党所属履歴なしでスキップ."""
        self._setup_election(mock_repos, election)
        mock_repos["election_member"].get_by_election_id.return_value = [
            ElectionMember(election_id=1, politician_id=1, result="当選", id=1),
        ]
        mock_repos["politician"].get_by_ids.return_value = [
            Politician(
                name="自民太郎",
                prefecture="東京都",
                district="",
                id=1,
            ),
        ]
        # 履歴なし → 空dict
        mock_repos["party_history"].get_current_by_politicians.return_value = {}
        mock_repos["group"].get_by_governing_body_id.return_value = [ldp_group]
        mock_repos["membership"].get_active_by_group.return_value = []
        mock_repos[
            "membership"
        ].create_membership.return_value = ParliamentaryGroupMembership(
            politician_id=1,
            parliamentary_group_id=100,
            start_date=ELECTION_DATE,
            id=1,
        )

        input_dto = LinkParliamentaryGroupInputDto(term_number=50)
        result = await use_case_with_history.execute(input_dto)

        # 履歴なし → 政党所属履歴なしでスキップ
        assert result.skipped_no_party == 1
        assert result.linked_count == 0
