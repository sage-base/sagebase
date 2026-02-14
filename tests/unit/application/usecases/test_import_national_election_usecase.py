"""国政選挙データインポートユースケースのテスト."""

from datetime import date
from unittest.mock import AsyncMock

import pytest

from src.application.dtos.national_election_import_dto import (
    ImportNationalElectionInputDto,
    ImportNationalElectionOutputDto,
)
from src.application.services.election_import_service import normalize_name
from src.application.usecases.import_national_election_usecase import (
    ImportNationalElectionUseCase,
)
from src.domain.entities.election import Election
from src.domain.entities.election_member import ElectionMember
from src.domain.entities.political_party import PoliticalParty
from src.domain.entities.politician import Politician
from src.domain.repositories.election_member_repository import ElectionMemberRepository
from src.domain.repositories.election_repository import ElectionRepository
from src.domain.repositories.political_party_repository import (
    PoliticalPartyRepository,
)
from src.domain.repositories.politician_repository import PoliticianRepository
from src.domain.value_objects.election_candidate import CandidateRecord, ElectionInfo


class TestNormalizeName:
    """名前正規化のテスト."""

    def test_half_width_space(self) -> None:
        assert normalize_name("小林 太郎") == "小林太郎"

    def test_full_width_space(self) -> None:
        assert normalize_name("小林\u3000太郎") == "小林太郎"

    def test_multiple_spaces(self) -> None:
        assert normalize_name("小林  \u3000 太郎") == "小林太郎"

    def test_no_space(self) -> None:
        assert normalize_name("小林太郎") == "小林太郎"


class TestImportNationalElectionUseCase:
    """インポートユースケースのテスト."""

    @pytest.fixture()
    def mock_repos(self) -> dict[str, AsyncMock]:
        """モックリポジトリを生成する."""
        return {
            "election": AsyncMock(spec=ElectionRepository),
            "election_member": AsyncMock(spec=ElectionMemberRepository),
            "politician": AsyncMock(spec=PoliticianRepository),
            "political_party": AsyncMock(spec=PoliticalPartyRepository),
        }

    @pytest.fixture()
    def mock_data_source(self) -> AsyncMock:
        """モックデータソースを生成する."""
        return AsyncMock()

    @pytest.fixture()
    def use_case(
        self, mock_repos: dict[str, AsyncMock], mock_data_source: AsyncMock
    ) -> ImportNationalElectionUseCase:
        """ユースケースインスタンスを生成する."""
        return ImportNationalElectionUseCase(
            election_repository=mock_repos["election"],
            election_member_repository=mock_repos["election_member"],
            politician_repository=mock_repos["politician"],
            political_party_repository=mock_repos["political_party"],
            election_data_source=mock_data_source,
        )

    @pytest.fixture()
    def sample_candidates(self) -> list[CandidateRecord]:
        """テスト用候補者データ."""
        return [
            CandidateRecord(
                name="田中 太郎",
                party_name="自由民主党",
                district_name="北海道第1区",
                prefecture="北海道",
                total_votes=50000,
                rank=1,
                is_elected=True,
            ),
            CandidateRecord(
                name="鈴木 花子",
                party_name="立憲民主党",
                district_name="北海道第1区",
                prefecture="北海道",
                total_votes=30000,
                rank=2,
                is_elected=False,
            ),
        ]

    # --- _match_politician テスト ---

    async def test_match_politician_single_match(
        self,
        use_case: ImportNationalElectionUseCase,
        mock_repos: dict[str, AsyncMock],
    ) -> None:
        """1件のマッチがある場合、matchedを返す."""
        existing = Politician(name="田中太郎", prefecture="北海道", district="", id=1)
        mock_repos["politician"].search_by_normalized_name.return_value = [existing]

        result, status = await use_case._import_service.match_politician(
            "田中 太郎", None
        )
        assert status == "matched"
        assert result is not None
        assert result.id == 1

    async def test_match_politician_no_match(
        self,
        use_case: ImportNationalElectionUseCase,
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
        use_case: ImportNationalElectionUseCase,
        mock_repos: dict[str, AsyncMock],
    ) -> None:
        """同姓同名で政党絞り込みにより1件になる場合、matchedを返す."""
        p1 = Politician(
            name="田中太郎",
            prefecture="東京都",
            district="",
            political_party_id=1,
            id=10,
        )
        p2 = Politician(
            name="田中太郎",
            prefecture="大阪府",
            district="",
            political_party_id=2,
            id=20,
        )
        mock_repos["politician"].search_by_normalized_name.return_value = [p1, p2]

        result, status = await use_case._import_service.match_politician("田中太郎", 1)
        assert status == "matched"
        assert result is not None
        assert result.id == 10

    async def test_match_politician_ambiguous_no_resolution(
        self,
        use_case: ImportNationalElectionUseCase,
        mock_repos: dict[str, AsyncMock],
    ) -> None:
        """同姓同名で政党でも絞り込めない場合、ambiguousを返す."""
        p1 = Politician(
            name="田中太郎",
            prefecture="東京都",
            district="",
            political_party_id=1,
            id=10,
        )
        p2 = Politician(
            name="田中太郎",
            prefecture="大阪府",
            district="",
            political_party_id=1,
            id=20,
        )
        mock_repos["politician"].search_by_normalized_name.return_value = [p1, p2]

        result, status = await use_case._import_service.match_politician("田中太郎", 1)
        assert status == "ambiguous"
        assert result is None

    # --- _resolve_party テスト ---

    async def test_resolve_party_existing(
        self,
        use_case: ImportNationalElectionUseCase,
        mock_repos: dict[str, AsyncMock],
    ) -> None:
        """既存政党が見つかる場合."""
        party = PoliticalParty(name="自由民主党", id=1)
        mock_repos["political_party"].get_by_name.return_value = party

        result, is_new = await use_case._import_service.resolve_party("自由民主党")
        assert result is not None
        assert result.id == 1
        assert is_new is False

    async def test_resolve_party_create_new(
        self,
        use_case: ImportNationalElectionUseCase,
        mock_repos: dict[str, AsyncMock],
    ) -> None:
        """新規政党を作成する場合."""
        mock_repos["political_party"].get_by_name.return_value = None
        new_party = PoliticalParty(name="新しい党", id=99)
        mock_repos["political_party"].create.return_value = new_party

        result, is_new = await use_case._import_service.resolve_party("新しい党")
        assert result is not None
        assert result.id == 99
        assert is_new is True
        mock_repos["political_party"].create.assert_called_once()

    async def test_resolve_party_empty_name(
        self,
        use_case: ImportNationalElectionUseCase,
    ) -> None:
        """空の政党名でNoneを返す."""
        result, is_new = await use_case._import_service.resolve_party("")
        assert result is None
        assert is_new is False

    async def test_resolve_party_caching(
        self,
        use_case: ImportNationalElectionUseCase,
        mock_repos: dict[str, AsyncMock],
    ) -> None:
        """政党キャッシュが効くことを確認."""
        party = PoliticalParty(name="自由民主党", id=1)
        mock_repos["political_party"].get_by_name.return_value = party

        # 1回目
        await use_case._import_service.resolve_party("自由民主党")
        # 2回目（キャッシュから）
        result, is_new = await use_case._import_service.resolve_party("自由民主党")

        assert result is not None
        assert result.id == 1
        assert is_new is False
        # get_by_nameは1回だけ呼ばれる
        assert mock_repos["political_party"].get_by_name.call_count == 1

    # --- _process_candidate テスト ---

    async def test_process_candidate_creates_election_member(
        self,
        use_case: ImportNationalElectionUseCase,
        mock_repos: dict[str, AsyncMock],
        sample_candidates: list[CandidateRecord],
    ) -> None:
        """候補者処理でElectionMemberが作成される."""
        party = PoliticalParty(name="自由民主党", id=1)
        mock_repos["political_party"].get_by_name.return_value = party

        politician = Politician(
            name="田中太郎", prefecture="北海道", district="", id=100
        )
        mock_repos["politician"].search_by_normalized_name.return_value = [politician]
        mock_repos["election_member"].create.return_value = ElectionMember(
            election_id=1, politician_id=100, result="当選", id=1
        )

        result_output = ImportNationalElectionOutputDto(election_number=50)
        await use_case._process_candidate(
            sample_candidates[0], election_id=1, output=result_output
        )

        assert result_output.matched_politicians == 1
        assert result_output.election_members_created == 1
        mock_repos["election_member"].create.assert_called_once()

    async def test_process_candidate_creates_new_politician(
        self,
        use_case: ImportNationalElectionUseCase,
        mock_repos: dict[str, AsyncMock],
        sample_candidates: list[CandidateRecord],
    ) -> None:
        """未マッチの候補者で新規政治家が作成される."""
        party = PoliticalParty(name="自由民主党", id=1)
        mock_repos["political_party"].get_by_name.return_value = party

        # マッチなし
        mock_repos["politician"].search_by_normalized_name.return_value = []
        new_politician = Politician(
            name="田中 太郎", prefecture="北海道", district="北海道第1区", id=200
        )
        mock_repos["politician"].create.return_value = new_politician
        mock_repos["election_member"].create.return_value = ElectionMember(
            election_id=1, politician_id=200, result="当選", id=1
        )

        result_output = ImportNationalElectionOutputDto(election_number=50)
        await use_case._process_candidate(
            sample_candidates[0], election_id=1, output=result_output
        )

        assert result_output.created_politicians == 1
        assert result_output.election_members_created == 1
        mock_repos["politician"].create.assert_called_once()

    async def test_process_candidate_ambiguous_skips(
        self,
        use_case: ImportNationalElectionUseCase,
        mock_repos: dict[str, AsyncMock],
        sample_candidates: list[CandidateRecord],
    ) -> None:
        """同姓同名でスキップされる場合."""
        mock_repos["political_party"].get_by_name.return_value = PoliticalParty(
            name="自由民主党", id=1
        )
        # 同姓同名で絞り込めない
        p1 = Politician(
            name="田中太郎",
            prefecture="東京都",
            district="",
            id=10,
            political_party_id=1,
        )
        p2 = Politician(
            name="田中太郎",
            prefecture="大阪府",
            district="",
            id=20,
            political_party_id=1,
        )
        mock_repos["politician"].search_by_normalized_name.return_value = [p1, p2]

        result_output = ImportNationalElectionOutputDto(election_number=50)
        await use_case._process_candidate(
            sample_candidates[0], election_id=1, output=result_output
        )

        assert result_output.skipped_ambiguous == 1
        assert result_output.election_members_created == 0

    async def test_process_candidate_duplicate_politician_skips(
        self,
        use_case: ImportNationalElectionUseCase,
        mock_repos: dict[str, AsyncMock],
        sample_candidates: list[CandidateRecord],
    ) -> None:
        """同一politician_idの重複がスキップされる."""
        party = PoliticalParty(name="自由民主党", id=1)
        mock_repos["political_party"].get_by_name.return_value = party

        politician = Politician(
            name="田中太郎", prefecture="北海道", district="", id=100
        )
        mock_repos["politician"].search_by_normalized_name.return_value = [politician]
        mock_repos["election_member"].create.return_value = ElectionMember(
            election_id=1, politician_id=100, result="当選", id=1
        )

        result_output = ImportNationalElectionOutputDto(election_number=50)

        # 1回目: 正常作成
        await use_case._process_candidate(
            sample_candidates[0], election_id=1, output=result_output
        )
        assert result_output.election_members_created == 1

        # 2回目: 同じpolitician_idでスキップ
        await use_case._process_candidate(
            sample_candidates[0], election_id=1, output=result_output
        )
        assert result_output.skipped_ambiguous == 1
        assert result_output.election_members_created == 1  # 増加しない

    async def test_process_candidate_new_party_increments_counter(
        self,
        use_case: ImportNationalElectionUseCase,
        mock_repos: dict[str, AsyncMock],
        sample_candidates: list[CandidateRecord],
    ) -> None:
        """新規政党作成でcreated_partiesカウンタが増加する."""
        mock_repos["political_party"].get_by_name.return_value = None
        new_party = PoliticalParty(name="自由民主党", id=1)
        mock_repos["political_party"].create.return_value = new_party

        mock_repos["politician"].search_by_normalized_name.return_value = []
        mock_repos["politician"].create.return_value = Politician(
            name="田中 太郎", prefecture="北海道", district="北海道第1区", id=200
        )
        mock_repos["election_member"].create.return_value = ElectionMember(
            election_id=1, politician_id=200, result="当選", id=1
        )

        result_output = ImportNationalElectionOutputDto(election_number=50)
        await use_case._process_candidate(
            sample_candidates[0], election_id=1, output=result_output
        )

        assert result_output.created_parties == 1

    # --- execute() テスト ---

    async def test_execute_dry_run(
        self,
        use_case: ImportNationalElectionUseCase,
        mock_repos: dict[str, AsyncMock],
        mock_data_source: AsyncMock,
        sample_candidates: list[CandidateRecord],
    ) -> None:
        """ドライランでDB書き込みが行われないことを確認."""
        input_dto = ImportNationalElectionInputDto(
            election_number=50,
            governing_body_id=1,
            dry_run=True,
        )

        mock_data_source.fetch_candidates.return_value = (
            ElectionInfo(election_number=50, election_date=date(2024, 10, 27)),
            sample_candidates,
        )

        result = await use_case.execute(input_dto)

        assert result.total_candidates == 2
        # DB操作は呼ばれない
        mock_repos["election"].create.assert_not_called()
        mock_repos["election_member"].create.assert_not_called()

    async def test_execute_full_import(
        self,
        use_case: ImportNationalElectionUseCase,
        mock_repos: dict[str, AsyncMock],
        mock_data_source: AsyncMock,
        sample_candidates: list[CandidateRecord],
    ) -> None:
        """非ドライランのフルインポートフロー."""
        input_dto = ImportNationalElectionInputDto(
            election_number=50,
            governing_body_id=1,
            dry_run=False,
        )

        # データソースモック
        mock_data_source.fetch_candidates.return_value = (
            ElectionInfo(election_number=50, election_date=date(2024, 10, 27)),
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
        mock_repos["election"].get_by_governing_body_and_term.return_value = None
        mock_repos["election"].create.return_value = election
        mock_repos["election_member"].delete_by_election_id.return_value = 0

        # 政党モック（両方とも新規作成）
        ldp = PoliticalParty(name="自由民主党", id=10)
        cdp = PoliticalParty(name="立憲民主党", id=20)
        mock_repos["political_party"].get_by_name.return_value = None
        mock_repos["political_party"].create.side_effect = [ldp, cdp]

        # 政治家モック（両方とも新規作成）
        pol1 = Politician(
            name="田中 太郎", prefecture="北海道", district="北海道第1区", id=100
        )
        pol2 = Politician(
            name="鈴木 花子", prefecture="北海道", district="北海道第1区", id=200
        )
        mock_repos["politician"].search_by_normalized_name.return_value = []
        mock_repos["politician"].create.side_effect = [pol1, pol2]

        # ElectionMemberモック
        mock_repos["election_member"].create.side_effect = [
            ElectionMember(election_id=1, politician_id=100, result="当選", id=1),
            ElectionMember(election_id=1, politician_id=200, result="落選", id=2),
        ]

        result = await use_case.execute(input_dto)

        assert result.election_id == 1
        assert result.total_candidates == 2
        assert result.created_politicians == 2
        assert result.created_parties == 2
        assert result.election_members_created == 2
        assert result.errors == 0

    async def test_execute_no_candidates_returns_error(
        self,
        use_case: ImportNationalElectionUseCase,
        mock_data_source: AsyncMock,
    ) -> None:
        """候補者データがない場合エラーを返す."""
        input_dto = ImportNationalElectionInputDto(
            election_number=50,
            governing_body_id=1,
        )
        mock_data_source.fetch_candidates.return_value = (None, [])

        result = await use_case.execute(input_dto)

        assert result.errors == 1
        assert "候補者データの取得に失敗" in result.error_details

    async def test_execute_idempotent_re_import(
        self,
        use_case: ImportNationalElectionUseCase,
        mock_repos: dict[str, AsyncMock],
        mock_data_source: AsyncMock,
        sample_candidates: list[CandidateRecord],
    ) -> None:
        """冪等性: 2回目実行で既存メンバーが削除されてから再作成される."""
        input_dto = ImportNationalElectionInputDto(
            election_number=50,
            governing_body_id=1,
        )

        # データソースモック
        mock_data_source.fetch_candidates.return_value = (
            ElectionInfo(election_number=50, election_date=date(2024, 10, 27)),
            sample_candidates,
        )

        # 既存Election（2回目のインポート想定）
        existing_election = Election(
            governing_body_id=1,
            term_number=50,
            election_date=date(2024, 10, 27),
            election_type="衆議院議員総選挙",
            id=1,
        )
        mock_repos[
            "election"
        ].get_by_governing_body_and_term.return_value = existing_election
        mock_repos["election_member"].delete_by_election_id.return_value = 5

        # 政党と政治家のモック
        ldp = PoliticalParty(name="自由民主党", id=10)
        cdp = PoliticalParty(name="立憲民主党", id=20)
        mock_repos["political_party"].get_by_name.side_effect = [ldp, cdp]

        pol1 = Politician(name="田中太郎", prefecture="北海道", district="", id=100)
        pol2 = Politician(name="鈴木花子", prefecture="北海道", district="", id=200)
        mock_repos["politician"].search_by_normalized_name.side_effect = [
            [pol1],
            [pol2],
        ]

        mock_repos["election_member"].create.side_effect = [
            ElectionMember(election_id=1, politician_id=100, result="当選", id=10),
            ElectionMember(election_id=1, politician_id=200, result="落選", id=11),
        ]

        result = await use_case.execute(input_dto)

        # 既存メンバーが削除されたことを確認
        mock_repos["election_member"].delete_by_election_id.assert_called_once_with(1)
        # 新しくElection作成はされない
        mock_repos["election"].create.assert_not_called()
        # ElectionMemberが再作成される
        assert result.election_members_created == 2
        assert result.matched_politicians == 2
        assert result.errors == 0

    async def test_execute_clears_caches(
        self,
        use_case: ImportNationalElectionUseCase,
        mock_data_source: AsyncMock,
    ) -> None:
        """execute()開始時にキャッシュがクリアされることを確認."""
        # キャッシュに事前にデータを入れる
        use_case._import_service._party_cache["test"] = PoliticalParty(
            name="test", id=1
        )
        use_case._processed_politician_ids.add(999)

        mock_data_source.fetch_candidates.return_value = (None, [])

        input_dto = ImportNationalElectionInputDto(
            election_number=50,
            governing_body_id=1,
        )
        await use_case.execute(input_dto)

        # キャッシュがクリアされている
        assert len(use_case._import_service._party_cache) == 0
        assert len(use_case._processed_politician_ids) == 0
