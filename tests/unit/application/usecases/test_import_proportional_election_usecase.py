"""比例代表選挙データインポートユースケースのテスト."""

from datetime import date
from unittest.mock import AsyncMock

import pytest

from src.application.dtos.proportional_election_import_dto import (
    ImportProportionalElectionInputDto,
    ImportProportionalElectionOutputDto,
)
from src.application.usecases.import_proportional_election_usecase import (
    ImportProportionalElectionUseCase,
)
from src.domain.entities.election import Election
from src.domain.entities.election_member import ElectionMember
from src.domain.entities.party_membership_history import PartyMembershipHistory
from src.domain.entities.political_party import PoliticalParty
from src.domain.entities.politician import Politician
from src.domain.repositories.election_member_repository import ElectionMemberRepository
from src.domain.repositories.election_repository import ElectionRepository
from src.domain.repositories.party_membership_history_repository import (
    PartyMembershipHistoryRepository,
)
from src.domain.repositories.political_party_repository import (
    PoliticalPartyRepository,
)
from src.domain.repositories.politician_repository import PoliticianRepository
from src.domain.value_objects.proportional_candidate import (
    ProportionalCandidateRecord,
    ProportionalElectionInfo,
)


class TestImportProportionalElectionUseCase:
    """比例代表インポートユースケースのテスト."""

    @pytest.fixture()
    def mock_repos(self) -> dict[str, AsyncMock]:
        """モックリポジトリを生成する."""
        return {
            "election": AsyncMock(spec=ElectionRepository),
            "election_member": AsyncMock(spec=ElectionMemberRepository),
            "politician": AsyncMock(spec=PoliticianRepository),
            "political_party": AsyncMock(spec=PoliticalPartyRepository),
            "party_membership_history": AsyncMock(
                spec=PartyMembershipHistoryRepository
            ),
        }

    @pytest.fixture()
    def mock_data_source(self) -> AsyncMock:
        """モックデータソースを生成する."""
        return AsyncMock()

    @pytest.fixture()
    def use_case(
        self, mock_repos: dict[str, AsyncMock], mock_data_source: AsyncMock
    ) -> ImportProportionalElectionUseCase:
        """ユースケースインスタンスを生成する."""
        return ImportProportionalElectionUseCase(
            election_repository=mock_repos["election"],
            election_member_repository=mock_repos["election_member"],
            politician_repository=mock_repos["politician"],
            political_party_repository=mock_repos["political_party"],
            proportional_data_source=mock_data_source,
            party_membership_history_repository=mock_repos["party_membership_history"],
        )

    @pytest.fixture()
    def sample_candidates(self) -> list[ProportionalCandidateRecord]:
        """テスト用比例代表候補者データ."""
        return [
            ProportionalCandidateRecord(
                name="渡辺 孝一",
                party_name="自由民主党",
                block_name="北海道",
                list_order=1,
                smd_result="落",
                loss_ratio=92.714,
                is_elected=True,
            ),
            ProportionalCandidateRecord(
                name="佐藤 花子",
                party_name="自由民主党",
                block_name="北海道",
                list_order=2,
                smd_result="",
                loss_ratio=None,
                is_elected=True,
            ),
            ProportionalCandidateRecord(
                name="田中 太郎",
                party_name="自由民主党",
                block_name="北海道",
                list_order=3,
                smd_result="当",
                loss_ratio=None,
                is_elected=True,
            ),
            ProportionalCandidateRecord(
                name="鈴木 次郎",
                party_name="自由民主党",
                block_name="北海道",
                list_order=4,
                smd_result="落",
                loss_ratio=80.0,
                is_elected=False,
            ),
        ]

    # --- 比例復活判定テスト ---

    async def test_process_candidate_proportional_revival(
        self,
        use_case: ImportProportionalElectionUseCase,
        mock_repos: dict[str, AsyncMock],
        sample_candidates: list[ProportionalCandidateRecord],
    ) -> None:
        """小選挙区落選 + 比例当選 → 比例復活."""
        party = PoliticalParty(name="自由民主党", id=1)
        mock_repos["political_party"].get_by_name.return_value = party

        politician = Politician(
            name="渡辺孝一", prefecture="北海道", district="", id=100
        )
        mock_repos["politician"].search_by_normalized_name.return_value = [politician]
        mock_repos["election_member"].create.return_value = ElectionMember(
            election_id=1,
            politician_id=100,
            result="比例復活",
            id=1,
        )

        output = ImportProportionalElectionOutputDto(election_number=50)
        await use_case._process_candidate(
            sample_candidates[0], election_id=1, output=output
        )

        assert output.proportional_revival == 1
        assert output.proportional_elected == 0
        assert output.election_members_created == 1

        # ElectionMemberの作成引数を確認
        created_member = mock_repos["election_member"].create.call_args[0][0]
        assert created_member.result == ElectionMember.RESULT_PROPORTIONAL_REVIVAL

    async def test_process_candidate_proportional_elected(
        self,
        use_case: ImportProportionalElectionUseCase,
        mock_repos: dict[str, AsyncMock],
        sample_candidates: list[ProportionalCandidateRecord],
    ) -> None:
        """比例単独候補 + 当選 → 比例当選."""
        party = PoliticalParty(name="自由民主党", id=1)
        mock_repos["political_party"].get_by_name.return_value = party

        politician = Politician(
            name="佐藤花子", prefecture="", district="北海道", id=200
        )
        mock_repos["politician"].search_by_normalized_name.return_value = [politician]
        mock_repos["election_member"].create.return_value = ElectionMember(
            election_id=1,
            politician_id=200,
            result="比例当選",
            id=2,
        )

        output = ImportProportionalElectionOutputDto(election_number=50)
        await use_case._process_candidate(
            sample_candidates[1], election_id=1, output=output
        )

        assert output.proportional_elected == 1
        assert output.proportional_revival == 0
        assert output.election_members_created == 1

        created_member = mock_repos["election_member"].create.call_args[0][0]
        assert created_member.result == ElectionMember.RESULT_PROPORTIONAL_ELECTED

    async def test_process_candidate_smd_winner_skipped(
        self,
        use_case: ImportProportionalElectionUseCase,
        sample_candidates: list[ProportionalCandidateRecord],
    ) -> None:
        """小選挙区当選者は比例レコード不要でスキップされる."""
        output = ImportProportionalElectionOutputDto(election_number=50)
        await use_case._process_candidate(
            sample_candidates[2], election_id=1, output=output
        )

        assert output.skipped_smd_winner == 1
        assert output.election_members_created == 0

    # --- 名寄せテスト ---

    async def test_match_politician_single_match(
        self,
        use_case: ImportProportionalElectionUseCase,
        mock_repos: dict[str, AsyncMock],
    ) -> None:
        """1件のマッチがある場合、matchedを返す."""
        existing = Politician(name="渡辺孝一", prefecture="北海道", district="", id=1)
        mock_repos["politician"].search_by_normalized_name.return_value = [existing]

        result, status = await use_case._import_service.match_politician(
            "渡辺 孝一", None
        )
        assert status == "matched"
        assert result is not None
        assert result.id == 1

    async def test_match_politician_no_match(
        self,
        use_case: ImportProportionalElectionUseCase,
        mock_repos: dict[str, AsyncMock],
    ) -> None:
        """マッチなしの場合、not_foundを返す."""
        mock_repos["politician"].search_by_normalized_name.return_value = []

        result, status = await use_case._import_service.match_politician(
            "新人 候補", None
        )
        assert status == "not_found"
        assert result is None

    async def test_match_politician_ambiguous_with_party_filter(
        self,
        use_case: ImportProportionalElectionUseCase,
        mock_repos: dict[str, AsyncMock],
    ) -> None:
        """同姓同名で政党絞り込みにより1件になる場合、matchedを返す."""
        p1 = Politician(
            name="田中太郎",
            prefecture="東京都",
            district="",
            id=10,
        )
        p2 = Politician(
            name="田中太郎",
            prefecture="大阪府",
            district="",
            id=20,
        )
        mock_repos["politician"].search_by_normalized_name.return_value = [p1, p2]

        # party_membership_history経由で政党を絞り込む
        history_p1 = PartyMembershipHistory(
            politician_id=10,
            political_party_id=1,
            start_date=date(2020, 1, 1),
            end_date=None,
        )
        mock_repos[
            "party_membership_history"
        ].get_current_by_politicians.return_value = {10: history_p1}

        result, status = await use_case._import_service.match_politician(
            "田中太郎", 1, election_date=date(2024, 10, 27)
        )
        assert status == "matched"
        assert result is not None
        assert result.id == 10

    # --- execute() テスト ---

    async def test_execute_dry_run(
        self,
        use_case: ImportProportionalElectionUseCase,
        mock_repos: dict[str, AsyncMock],
        mock_data_source: AsyncMock,
        sample_candidates: list[ProportionalCandidateRecord],
    ) -> None:
        """ドライランでDB書き込みが行われないことを確認."""
        input_dto = ImportProportionalElectionInputDto(
            election_number=50,
            governing_body_id=1,
            dry_run=True,
        )

        mock_data_source.fetch_proportional_candidates.return_value = (
            ProportionalElectionInfo(
                election_number=50, election_date=date(2024, 10, 27)
            ),
            sample_candidates,
        )

        result = await use_case.execute(input_dto)

        assert result.total_candidates == 4
        assert result.elected_candidates == 3
        mock_repos["election"].create.assert_not_called()
        mock_repos["election_member"].create.assert_not_called()

    async def test_execute_full_import(
        self,
        use_case: ImportProportionalElectionUseCase,
        mock_repos: dict[str, AsyncMock],
        mock_data_source: AsyncMock,
        sample_candidates: list[ProportionalCandidateRecord],
    ) -> None:
        """非ドライランのフルインポートフロー."""
        input_dto = ImportProportionalElectionInputDto(
            election_number=50,
            governing_body_id=1,
            dry_run=False,
        )

        mock_data_source.fetch_proportional_candidates.return_value = (
            ProportionalElectionInfo(
                election_number=50, election_date=date(2024, 10, 27)
            ),
            sample_candidates,
        )

        # Election作成モック
        election = Election(
            governing_body_id=1,
            term_number=50,
            election_date=date(2024, 10, 27),
            election_type="衆議院議員総選挙",
            id=1,
        )
        mock_repos["election"].get_by_governing_body_and_term.return_value = election
        mock_repos["election_member"].delete_by_election_id_and_results.return_value = 0

        # 政党モック
        ldp = PoliticalParty(name="自由民主党", id=10)
        mock_repos["political_party"].get_by_name.return_value = ldp

        # 政治家モック
        pol1 = Politician(name="渡辺孝一", prefecture="北海道", district="", id=100)
        pol2 = Politician(name="佐藤花子", prefecture="", district="北海道", id=200)
        mock_repos["politician"].search_by_normalized_name.side_effect = [
            [pol1],  # 渡辺（比例復活）
            [pol2],  # 佐藤（比例当選）
            # 田中は小選挙区当選でスキップ
        ]

        mock_repos["election_member"].create.side_effect = [
            ElectionMember(election_id=1, politician_id=100, result="比例復活", id=1),
            ElectionMember(election_id=1, politician_id=200, result="比例当選", id=2),
        ]

        result = await use_case.execute(input_dto)

        assert result.election_id == 1
        assert result.total_candidates == 4
        assert result.elected_candidates == 3
        assert result.proportional_revival == 1  # 渡辺
        assert result.proportional_elected == 1  # 佐藤
        assert result.skipped_smd_winner == 1  # 田中（小選挙区当選）
        assert result.election_members_created == 2
        assert result.errors == 0

    async def test_execute_deletes_existing_proportional_members(
        self,
        use_case: ImportProportionalElectionUseCase,
        mock_repos: dict[str, AsyncMock],
        mock_data_source: AsyncMock,
        sample_candidates: list[ProportionalCandidateRecord],
    ) -> None:
        """再実行時に既存の比例メンバーのみ削除されることを確認."""
        input_dto = ImportProportionalElectionInputDto(
            election_number=50,
            governing_body_id=1,
            dry_run=False,
        )

        mock_data_source.fetch_proportional_candidates.return_value = (
            ProportionalElectionInfo(
                election_number=50, election_date=date(2024, 10, 27)
            ),
            sample_candidates,
        )

        election = Election(
            governing_body_id=1,
            term_number=50,
            election_date=date(2024, 10, 27),
            election_type="衆議院議員総選挙",
            id=1,
        )
        mock_repos["election"].get_by_governing_body_and_term.return_value = election
        mock_repos["election_member"].delete_by_election_id_and_results.return_value = 5

        ldp = PoliticalParty(name="自由民主党", id=10)
        mock_repos["political_party"].get_by_name.return_value = ldp

        pol1 = Politician(name="渡辺孝一", prefecture="北海道", district="", id=100)
        pol2 = Politician(name="佐藤花子", prefecture="", district="北海道", id=200)
        mock_repos["politician"].search_by_normalized_name.side_effect = [
            [pol1],
            [pol2],
        ]
        mock_repos["election_member"].create.side_effect = [
            ElectionMember(election_id=1, politician_id=100, result="比例復活", id=1),
            ElectionMember(election_id=1, politician_id=200, result="比例当選", id=2),
        ]

        await use_case.execute(input_dto)

        # 比例代表の結果値のみで削除が呼ばれることを確認
        mock_repos[
            "election_member"
        ].delete_by_election_id_and_results.assert_called_once_with(
            1,
            [
                ElectionMember.RESULT_PROPORTIONAL_ELECTED,
                ElectionMember.RESULT_PROPORTIONAL_REVIVAL,
            ],
        )
        # delete_by_election_id（全削除）は呼ばれないことを確認
        mock_repos["election_member"].delete_by_election_id.assert_not_called()

    async def test_execute_no_candidates_returns_error(
        self,
        use_case: ImportProportionalElectionUseCase,
        mock_data_source: AsyncMock,
    ) -> None:
        """候補者データがない場合エラーを返す."""
        input_dto = ImportProportionalElectionInputDto(
            election_number=50,
            governing_body_id=1,
        )
        mock_data_source.fetch_proportional_candidates.return_value = (None, [])

        result = await use_case.execute(input_dto)

        assert result.errors == 1
        assert "比例代表候補者データの取得に失敗" in result.error_details

    async def test_execute_clears_caches(
        self,
        use_case: ImportProportionalElectionUseCase,
        mock_data_source: AsyncMock,
    ) -> None:
        """execute()開始時にキャッシュがクリアされることを確認."""
        use_case._import_service._party_cache["test"] = PoliticalParty(
            name="test", id=1
        )
        use_case._processed_politician_ids.add(999)

        mock_data_source.fetch_proportional_candidates.return_value = (None, [])

        input_dto = ImportProportionalElectionInputDto(
            election_number=50,
            governing_body_id=1,
        )
        await use_case.execute(input_dto)

        assert len(use_case._import_service._party_cache) == 0
        assert len(use_case._processed_politician_ids) == 0

    async def test_process_candidate_duplicate_politician_skips(
        self,
        use_case: ImportProportionalElectionUseCase,
        mock_repos: dict[str, AsyncMock],
    ) -> None:
        """同一politician_idの重複がスキップされる."""
        party = PoliticalParty(name="自由民主党", id=1)
        mock_repos["political_party"].get_by_name.return_value = party

        politician = Politician(
            name="渡辺孝一", prefecture="北海道", district="", id=100
        )
        mock_repos["politician"].search_by_normalized_name.return_value = [politician]
        mock_repos["election_member"].create.return_value = ElectionMember(
            election_id=1, politician_id=100, result="比例復活", id=1
        )

        candidate = ProportionalCandidateRecord(
            name="渡辺 孝一",
            party_name="自由民主党",
            block_name="北海道",
            list_order=1,
            smd_result="落",
            loss_ratio=92.714,
            is_elected=True,
        )

        output = ImportProportionalElectionOutputDto(election_number=50)

        # 1回目: 正常作成
        await use_case._process_candidate(candidate, election_id=1, output=output)
        assert output.election_members_created == 1

        # 2回目: 同じpolitician_idでスキップ
        await use_case._process_candidate(candidate, election_id=1, output=output)
        assert output.skipped_duplicate == 1
        assert output.election_members_created == 1  # 増加しない

    async def test_process_candidate_creates_new_politician(
        self,
        use_case: ImportProportionalElectionUseCase,
        mock_repos: dict[str, AsyncMock],
    ) -> None:
        """未マッチの候補者で新規政治家が作成される."""
        party = PoliticalParty(name="自由民主党", id=1)
        mock_repos["political_party"].get_by_name.return_value = party

        mock_repos["politician"].search_by_normalized_name.return_value = []
        new_politician = Politician(
            name="佐藤 花子", prefecture="", district="北海道", id=200
        )
        mock_repos["politician"].create.return_value = new_politician
        mock_repos["election_member"].create.return_value = ElectionMember(
            election_id=1, politician_id=200, result="比例当選", id=1
        )

        candidate = ProportionalCandidateRecord(
            name="佐藤 花子",
            party_name="自由民主党",
            block_name="北海道",
            list_order=2,
            smd_result="",
            loss_ratio=None,
            is_elected=True,
        )

        output = ImportProportionalElectionOutputDto(election_number=50)
        await use_case._process_candidate(candidate, election_id=1, output=output)

        assert output.created_politicians == 1
        assert output.election_members_created == 1
        mock_repos["politician"].create.assert_called_once()
