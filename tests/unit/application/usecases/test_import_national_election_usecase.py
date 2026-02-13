"""国政選挙データインポートユースケースのテスト."""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from src.application.dtos.national_election_import_dto import (
    CandidateRecord,
    ImportNationalElectionInputDto,
)
from src.application.usecases.import_national_election_usecase import (
    ImportNationalElectionUseCase,
    normalize_name,
)
from src.domain.entities.election_member import ElectionMember
from src.domain.entities.political_party import PoliticalParty
from src.domain.entities.politician import Politician
from src.domain.repositories.election_member_repository import ElectionMemberRepository
from src.domain.repositories.election_repository import ElectionRepository
from src.domain.repositories.political_party_repository import (
    PoliticalPartyRepository,
)
from src.domain.repositories.politician_repository import PoliticianRepository


class TestNormalizeName:
    """名前正規化のテスト."""

    def test_half_width_space(self) -> None:
        assert normalize_name("小林 太郎") == "小林太郎"

    def test_full_width_space(self) -> None:
        assert normalize_name("小林　太郎") == "小林太郎"

    def test_multiple_spaces(self) -> None:
        assert normalize_name("小林  　 太郎") == "小林太郎"

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
    def use_case(
        self, mock_repos: dict[str, AsyncMock]
    ) -> ImportNationalElectionUseCase:
        """ユースケースインスタンスを生成する."""
        return ImportNationalElectionUseCase(
            election_repository=mock_repos["election"],
            election_member_repository=mock_repos["election_member"],
            politician_repository=mock_repos["politician"],
            political_party_repository=mock_repos["political_party"],
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

    async def test_match_politician_single_match(
        self,
        use_case: ImportNationalElectionUseCase,
        mock_repos: dict[str, AsyncMock],
    ) -> None:
        """1件のマッチがある場合、matchedを返す."""
        existing = Politician(name="田中太郎", prefecture="北海道", district="", id=1)
        mock_repos["politician"].search_by_normalized_name.return_value = [existing]

        result, status = await use_case._match_politician("田中 太郎", None)
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

        result, status = await use_case._match_politician("新人 候補", None)
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

        result, status = await use_case._match_politician("田中太郎", 1)
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

        result, status = await use_case._match_politician("田中太郎", 1)
        assert status == "ambiguous"
        assert result is None

    async def test_resolve_party_existing(
        self,
        use_case: ImportNationalElectionUseCase,
        mock_repos: dict[str, AsyncMock],
    ) -> None:
        """既存政党が見つかる場合."""
        party = PoliticalParty(name="自由民主党", id=1)
        mock_repos["political_party"].get_by_name.return_value = party

        result = await use_case._resolve_party("自由民主党")
        assert result is not None
        assert result.id == 1

    async def test_resolve_party_create_new(
        self,
        use_case: ImportNationalElectionUseCase,
        mock_repos: dict[str, AsyncMock],
    ) -> None:
        """新規政党を作成する場合."""
        mock_repos["political_party"].get_by_name.return_value = None
        new_party = PoliticalParty(name="新しい党", id=99)
        mock_repos["political_party"].create.return_value = new_party

        result = await use_case._resolve_party("新しい党")
        assert result is not None
        assert result.id == 99
        mock_repos["political_party"].create.assert_called_once()

    async def test_resolve_party_caching(
        self,
        use_case: ImportNationalElectionUseCase,
        mock_repos: dict[str, AsyncMock],
    ) -> None:
        """政党キャッシュが効くことを確認."""
        party = PoliticalParty(name="自由民主党", id=1)
        mock_repos["political_party"].get_by_name.return_value = party

        # 1回目
        await use_case._resolve_party("自由民主党")
        # 2回目（キャッシュから）
        result = await use_case._resolve_party("自由民主党")

        assert result is not None
        assert result.id == 1
        # get_by_nameは1回だけ呼ばれる
        assert mock_repos["political_party"].get_by_name.call_count == 1

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

        from src.application.dtos.national_election_import_dto import (
            ImportNationalElectionOutputDto,
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

        from src.application.dtos.national_election_import_dto import (
            ImportNationalElectionOutputDto,
        )

        result_output = ImportNationalElectionOutputDto(election_number=50)
        await use_case._process_candidate(
            sample_candidates[0], election_id=1, output=result_output
        )

        assert result_output.created_politicians == 1
        assert result_output.election_members_created == 1
        mock_repos["politician"].create.assert_called_once()

    async def test_execute_dry_run(
        self,
        use_case: ImportNationalElectionUseCase,
        mock_repos: dict[str, AsyncMock],
        sample_candidates: list[CandidateRecord],
        tmp_path: object,
    ) -> None:
        """ドライランでDB書き込みが行われないことを確認."""
        input_dto = ImportNationalElectionInputDto(
            election_number=50,
            governing_body_id=1,
            dry_run=True,
        )

        # スクレイパーとパーサーをモック
        with (
            patch(
                "src.application.usecases.import_national_election_usecase.fetch_xls_urls"
            ) as mock_fetch,
            patch(
                "src.application.usecases.import_national_election_usecase.download_xls_files"
            ) as mock_download,
            patch(
                "src.application.usecases.import_national_election_usecase.parse_xls_file"
            ) as mock_parse,
        ):
            mock_fetch.return_value = [MagicMock()]
            mock_download.return_value = [(MagicMock(), MagicMock())]
            mock_parse.return_value = (
                MagicMock(election_date=None),
                sample_candidates,
            )

            result = await use_case.execute(input_dto)

        assert result.total_candidates == 2
        # DB操作は呼ばれない
        mock_repos["election"].create.assert_not_called()
        mock_repos["election_member"].create.assert_not_called()
