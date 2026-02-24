"""参議院選挙データインポートユースケースのテスト."""

from datetime import date
from pathlib import Path
from unittest.mock import AsyncMock

import pytest

from src.application.dtos.sangiin_election_import_dto import (
    ImportSangiinElectionInputDto,
)
from src.application.usecases.import_sangiin_election_usecase import (
    ImportSangiinElectionUseCase,
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
from src.domain.value_objects.sangiin_candidate import SangiinCandidateRecord


class TestImportSangiinElectionUseCase:
    """参議院選挙インポートユースケースのテスト."""

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
    ) -> ImportSangiinElectionUseCase:
        """ユースケースインスタンスを生成する."""
        return ImportSangiinElectionUseCase(
            election_repository=mock_repos["election"],
            election_member_repository=mock_repos["election_member"],
            politician_repository=mock_repos["politician"],
            political_party_repository=mock_repos["political_party"],
            data_source=mock_data_source,
        )

    @pytest.fixture()
    def sample_councillors(self) -> list[SangiinCandidateRecord]:
        """テスト用議員データ."""
        return [
            SangiinCandidateRecord(
                name="田中太郎",
                furigana="たなかたろう",
                party_name="自由民主党",
                district_name="東京都",
                elected_years=[2022, 2016],
                election_count=2,
                profile_url="https://example.com/tanaka",
                is_proportional=False,
            ),
            SangiinCandidateRecord(
                name="鈴木花子",
                furigana="すずきはなこ",
                party_name="立憲民主党",
                district_name="比例",
                elected_years=[2019],
                election_count=1,
                profile_url=None,
                is_proportional=True,
            ),
        ]

    # --- execute() テスト ---

    async def test_execute_dry_run(
        self,
        use_case: ImportSangiinElectionUseCase,
        mock_repos: dict[str, AsyncMock],
        mock_data_source: AsyncMock,
        sample_councillors: list[SangiinCandidateRecord],
    ) -> None:
        """ドライランでDB書き込みが行われないことを確認."""
        input_dto = ImportSangiinElectionInputDto(
            file_path=Path("/tmp/giin.json"),
            governing_body_id=1,
            dry_run=True,
        )
        mock_data_source.fetch_councillors.return_value = sample_councillors

        result = await use_case.execute(input_dto)

        assert result.total_councillors == 2
        mock_repos["election"].create.assert_not_called()
        mock_repos["election_member"].create.assert_not_called()

    async def test_execute_no_data_returns_error(
        self,
        use_case: ImportSangiinElectionUseCase,
        mock_data_source: AsyncMock,
    ) -> None:
        """議員データがない場合エラーを返す."""
        input_dto = ImportSangiinElectionInputDto(
            file_path=Path("/tmp/giin.json"),
            governing_body_id=1,
        )
        mock_data_source.fetch_councillors.return_value = []

        result = await use_case.execute(input_dto)

        assert result.errors == 1
        assert "議員データの取得に失敗" in result.error_details

    async def test_execute_full_import(
        self,
        use_case: ImportSangiinElectionUseCase,
        mock_repos: dict[str, AsyncMock],
        mock_data_source: AsyncMock,
    ) -> None:
        """フルインポートの正常系テスト（選挙区+比例の議員）."""
        councillors = [
            SangiinCandidateRecord(
                name="山田一郎",
                furigana="やまだいちろう",
                party_name="自由民主党",
                district_name="東京都",
                elected_years=[2022],
                election_count=1,
                profile_url=None,
                is_proportional=False,
            ),
            SangiinCandidateRecord(
                name="佐藤二郎",
                furigana="さとうじろう",
                party_name="立憲民主党",
                district_name="比例",
                elected_years=[2022],
                election_count=1,
                profile_url=None,
                is_proportional=True,
            ),
        ]
        input_dto = ImportSangiinElectionInputDto(
            file_path=Path("/tmp/giin.json"),
            governing_body_id=1,
            dry_run=False,
        )
        mock_data_source.fetch_councillors.return_value = councillors

        # Election作成モック
        election_26 = Election(
            governing_body_id=1,
            term_number=26,
            election_date=date(2022, 7, 1),
            election_type="参議院議員通常選挙",
            id=100,
        )
        mock_repos["election"].get_by_governing_body_and_term.return_value = None
        mock_repos["election"].create.return_value = election_26
        mock_repos["election_member"].delete_by_election_id.return_value = 0

        # 政党モック
        ldp = PoliticalParty(name="自由民主党", id=10)
        cdp = PoliticalParty(name="立憲民主党", id=20)
        mock_repos["political_party"].get_by_name.return_value = None
        mock_repos["political_party"].create.side_effect = [ldp, cdp]

        # 政治家モック（新規作成）
        pol1 = Politician(
            name="山田一郎", prefecture="東京都", district="東京都", id=100
        )
        pol2 = Politician(name="佐藤二郎", prefecture="", district="比例", id=200)
        mock_repos["politician"].search_by_normalized_name.return_value = []
        mock_repos["politician"].create.side_effect = [pol1, pol2]

        # ElectionMemberモック
        mock_repos["election_member"].create.side_effect = [
            ElectionMember(election_id=100, politician_id=100, result="当選", id=1),
            ElectionMember(election_id=100, politician_id=200, result="比例当選", id=2),
        ]

        result = await use_case.execute(input_dto)

        assert result.total_councillors == 2
        assert result.created_politicians == 2
        assert result.created_parties == 2
        assert result.election_members_created == 2
        assert result.errors == 0

    async def test_result_type_constituency_vs_proportional(
        self,
        use_case: ImportSangiinElectionUseCase,
        mock_repos: dict[str, AsyncMock],
        mock_data_source: AsyncMock,
    ) -> None:
        """選挙区は「当選」、比例は「比例当選」の判定."""
        councillors = [
            SangiinCandidateRecord(
                name="選挙区議員",
                furigana="せんきょくぎいん",
                party_name="自民",
                district_name="北海道",
                elected_years=[2022],
                election_count=1,
                profile_url=None,
                is_proportional=False,
            ),
            SangiinCandidateRecord(
                name="比例議員",
                furigana="ひれいぎいん",
                party_name="自民",
                district_name="比例",
                elected_years=[2022],
                election_count=1,
                profile_url=None,
                is_proportional=True,
            ),
        ]
        input_dto = ImportSangiinElectionInputDto(
            file_path=Path("/tmp/giin.json"),
            governing_body_id=1,
        )
        mock_data_source.fetch_councillors.return_value = councillors

        # Election
        election = Election(
            governing_body_id=1,
            term_number=26,
            election_date=date(2022, 7, 1),
            election_type="参議院議員通常選挙",
            id=1,
        )
        mock_repos["election"].get_by_governing_body_and_term.return_value = None
        mock_repos["election"].create.return_value = election
        mock_repos["election_member"].delete_by_election_id.return_value = 0

        # 政党
        party = PoliticalParty(name="自民", id=1)
        mock_repos["political_party"].get_by_name.return_value = party

        # 政治家
        mock_repos["politician"].search_by_normalized_name.return_value = []
        pol1 = Politician(
            name="選挙区議員", prefecture="北海道", district="北海道", id=1
        )
        pol2 = Politician(name="比例議員", prefecture="", district="比例", id=2)
        mock_repos["politician"].create.side_effect = [pol1, pol2]

        # ElectionMember: createの引数をキャプチャ
        created_members: list[ElectionMember] = []

        async def capture_create(member: ElectionMember) -> ElectionMember:
            created_members.append(member)
            return ElectionMember(
                election_id=member.election_id,
                politician_id=member.politician_id,
                result=member.result,
                id=len(created_members),
            )

        mock_repos["election_member"].create.side_effect = capture_create

        await use_case.execute(input_dto)

        assert len(created_members) == 2
        assert created_members[0].result == "当選"
        assert created_members[1].result == "比例当選"

    async def test_multiple_elected_years_creates_multiple_members(
        self,
        use_case: ImportSangiinElectionUseCase,
        mock_repos: dict[str, AsyncMock],
        mock_data_source: AsyncMock,
    ) -> None:
        """複数の当選年を持つ議員は各回次でElectionMemberが作成される."""
        councillors = [
            SangiinCandidateRecord(
                name="田中太郎",
                furigana="たなかたろう",
                party_name="自民",
                district_name="東京都",
                elected_years=[2022, 2016],
                election_count=2,
                profile_url=None,
                is_proportional=False,
            ),
        ]
        input_dto = ImportSangiinElectionInputDto(
            file_path=Path("/tmp/giin.json"),
            governing_body_id=1,
        )
        mock_data_source.fetch_councillors.return_value = councillors

        # 各回次のElection
        election_26 = Election(
            governing_body_id=1,
            term_number=26,
            election_date=date(2022, 7, 1),
            id=100,
        )
        election_24 = Election(
            governing_body_id=1,
            term_number=24,
            election_date=date(2016, 7, 1),
            id=200,
        )
        mock_repos["election"].get_by_governing_body_and_term.return_value = None
        mock_repos["election"].create.side_effect = [election_26, election_24]
        mock_repos["election_member"].delete_by_election_id.return_value = 0

        party = PoliticalParty(name="自民", id=1)
        mock_repos["political_party"].get_by_name.return_value = party

        politician = Politician(
            name="田中太郎", prefecture="東京都", district="", id=10
        )
        mock_repos["politician"].search_by_normalized_name.return_value = [politician]

        mock_repos["election_member"].create.side_effect = [
            ElectionMember(election_id=100, politician_id=10, result="当選", id=1),
            ElectionMember(election_id=200, politician_id=10, result="当選", id=2),
        ]

        result = await use_case.execute(input_dto)

        assert result.election_members_created == 2
        assert result.matched_politicians == 1
        assert result.elections_created == 2

    async def test_unsupported_year_skipped(
        self,
        use_case: ImportSangiinElectionUseCase,
        mock_repos: dict[str, AsyncMock],
        mock_data_source: AsyncMock,
    ) -> None:
        """対応表にない当選年はスキップされる."""
        councillors = [
            SangiinCandidateRecord(
                name="古い議員",
                furigana="ふるいぎいん",
                party_name="自民",
                district_name="東京都",
                elected_years=[1998],  # 対応表にない年
                election_count=1,
                profile_url=None,
                is_proportional=False,
            ),
        ]
        input_dto = ImportSangiinElectionInputDto(
            file_path=Path("/tmp/giin.json"),
            governing_body_id=1,
        )
        mock_data_source.fetch_councillors.return_value = councillors

        party = PoliticalParty(name="自民", id=1)
        mock_repos["political_party"].get_by_name.return_value = party

        politician = Politician(name="古い議員", prefecture="東京都", district="", id=1)
        mock_repos["politician"].search_by_normalized_name.return_value = [politician]

        result = await use_case.execute(input_dto)

        assert result.election_members_created == 0
        assert result.errors == 0

    async def test_ambiguous_politician_skips(
        self,
        use_case: ImportSangiinElectionUseCase,
        mock_repos: dict[str, AsyncMock],
        mock_data_source: AsyncMock,
    ) -> None:
        """同姓同名でスキップされる場合."""
        councillors = [
            SangiinCandidateRecord(
                name="田中太郎",
                furigana="たなかたろう",
                party_name="自民",
                district_name="東京都",
                elected_years=[2022],
                election_count=1,
                profile_url=None,
                is_proportional=False,
            ),
        ]
        input_dto = ImportSangiinElectionInputDto(
            file_path=Path("/tmp/giin.json"),
            governing_body_id=1,
        )
        mock_data_source.fetch_councillors.return_value = councillors

        party = PoliticalParty(name="自民", id=1)
        mock_repos["political_party"].get_by_name.return_value = party

        # 同姓同名の政治家
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

        result = await use_case.execute(input_dto)

        assert result.skipped_ambiguous == 1
        assert result.election_members_created == 0

    async def test_duplicate_politician_in_same_election_skips(
        self,
        use_case: ImportSangiinElectionUseCase,
        mock_repos: dict[str, AsyncMock],
        mock_data_source: AsyncMock,
    ) -> None:
        """同一回次内で同じ政治家の重複がスキップされる."""
        # 同じ議員が2行ある（異常データ）
        councillors = [
            SangiinCandidateRecord(
                name="田中太郎",
                furigana="たなかたろう",
                party_name="自民",
                district_name="東京都",
                elected_years=[2022],
                election_count=1,
                profile_url=None,
                is_proportional=False,
            ),
            SangiinCandidateRecord(
                name="田中太郎",
                furigana="たなかたろう",
                party_name="自民",
                district_name="東京都",
                elected_years=[2022],
                election_count=1,
                profile_url=None,
                is_proportional=False,
            ),
        ]
        input_dto = ImportSangiinElectionInputDto(
            file_path=Path("/tmp/giin.json"),
            governing_body_id=1,
        )
        mock_data_source.fetch_councillors.return_value = councillors

        election = Election(
            governing_body_id=1,
            term_number=26,
            election_date=date(2022, 7, 1),
            id=1,
        )
        mock_repos["election"].get_by_governing_body_and_term.return_value = None
        mock_repos["election"].create.return_value = election
        mock_repos["election_member"].delete_by_election_id.return_value = 0

        party = PoliticalParty(name="自民", id=1)
        mock_repos["political_party"].get_by_name.return_value = party

        politician = Politician(
            name="田中太郎", prefecture="東京都", district="", id=10
        )
        mock_repos["politician"].search_by_normalized_name.return_value = [politician]
        mock_repos["election_member"].create.return_value = ElectionMember(
            election_id=1, politician_id=10, result="当選", id=1
        )

        result = await use_case.execute(input_dto)

        assert result.election_members_created == 1
        assert result.skipped_duplicate == 1

    async def test_execute_idempotent(
        self,
        use_case: ImportSangiinElectionUseCase,
        mock_repos: dict[str, AsyncMock],
        mock_data_source: AsyncMock,
    ) -> None:
        """冪等性: 既存Electionのメンバーが削除されてから再作成される."""
        councillors = [
            SangiinCandidateRecord(
                name="田中太郎",
                furigana="たなかたろう",
                party_name="自民",
                district_name="東京都",
                elected_years=[2022],
                election_count=1,
                profile_url=None,
                is_proportional=False,
            ),
        ]
        input_dto = ImportSangiinElectionInputDto(
            file_path=Path("/tmp/giin.json"),
            governing_body_id=1,
        )
        mock_data_source.fetch_councillors.return_value = councillors

        # 既存Election
        existing_election = Election(
            governing_body_id=1,
            term_number=26,
            election_date=date(2022, 7, 1),
            election_type="参議院議員通常選挙",
            id=1,
        )
        mock_repos[
            "election"
        ].get_by_governing_body_and_term.return_value = existing_election
        mock_repos["election_member"].delete_by_election_id.return_value = 5

        party = PoliticalParty(name="自民", id=1)
        mock_repos["political_party"].get_by_name.return_value = party

        politician = Politician(
            name="田中太郎", prefecture="東京都", district="", id=10
        )
        mock_repos["politician"].search_by_normalized_name.return_value = [politician]
        mock_repos["election_member"].create.return_value = ElectionMember(
            election_id=1, politician_id=10, result="当選", id=1
        )

        result = await use_case.execute(input_dto)

        # 既存メンバーが削除されたことを確認
        mock_repos["election_member"].delete_by_election_id.assert_called_once_with(1)
        # Electionは新規作成されない
        mock_repos["election"].create.assert_not_called()
        assert result.elections_created == 0
        # ElectionMemberが再作成される
        assert result.election_members_created == 1
        assert result.matched_politicians == 1

    async def test_execute_clears_caches(
        self,
        use_case: ImportSangiinElectionUseCase,
        mock_data_source: AsyncMock,
    ) -> None:
        """execute()開始時にキャッシュがクリアされることを確認."""
        use_case._import_service._party_cache["test"] = PoliticalParty(
            name="test", id=1
        )
        use_case._processed_politician_ids[26] = {999}

        mock_data_source.fetch_councillors.return_value = []

        input_dto = ImportSangiinElectionInputDto(
            file_path=Path("/tmp/giin.json"),
            governing_body_id=1,
        )
        await use_case.execute(input_dto)

        assert len(use_case._import_service._party_cache) == 0
        assert len(use_case._processed_politician_ids) == 0
