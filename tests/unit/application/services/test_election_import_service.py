"""選挙インポート共通サービスのテスト."""

from datetime import date
from unittest.mock import AsyncMock

import pytest

from src.application.services.election_import_service import (
    ElectionImportService,
    normalize_name,
)
from src.domain.entities.election import Election
from src.domain.entities.political_party import PoliticalParty
from src.domain.entities.politician import Politician
from src.domain.repositories.election_repository import ElectionRepository
from src.domain.repositories.political_party_repository import (
    PoliticalPartyRepository,
)
from src.domain.repositories.politician_repository import PoliticianRepository


class TestNormalizeName:
    """名前正規化関数のテスト."""

    def test_half_width_space(self) -> None:
        assert normalize_name("渡辺 孝一") == "渡辺孝一"

    def test_full_width_space(self) -> None:
        assert normalize_name("渡辺\u3000孝一") == "渡辺孝一"

    def test_multiple_spaces(self) -> None:
        assert normalize_name("渡辺 　孝一") == "渡辺孝一"

    def test_no_space(self) -> None:
        assert normalize_name("渡辺孝一") == "渡辺孝一"


class TestElectionImportService:
    """選挙インポート共通サービスのテスト."""

    @pytest.fixture()
    def mock_politician_repo(self) -> AsyncMock:
        return AsyncMock(spec=PoliticianRepository)

    @pytest.fixture()
    def mock_party_repo(self) -> AsyncMock:
        return AsyncMock(spec=PoliticalPartyRepository)

    @pytest.fixture()
    def service(
        self, mock_politician_repo: AsyncMock, mock_party_repo: AsyncMock
    ) -> ElectionImportService:
        return ElectionImportService(
            politician_repository=mock_politician_repo,
            political_party_repository=mock_party_repo,
        )

    # --- resolve_party ---

    async def test_resolve_party_existing(
        self, service: ElectionImportService, mock_party_repo: AsyncMock
    ) -> None:
        """既存の政党が返される."""
        party = PoliticalParty(name="自由民主党", id=1)
        mock_party_repo.get_by_name.return_value = party

        result, is_new = await service.resolve_party("自由民主党")
        assert result == party
        assert is_new is False

    async def test_resolve_party_new(
        self, service: ElectionImportService, mock_party_repo: AsyncMock
    ) -> None:
        """新規政党が作成される."""
        mock_party_repo.get_by_name.return_value = None
        created = PoliticalParty(name="新党", id=2)
        mock_party_repo.create.return_value = created

        result, is_new = await service.resolve_party("新党")
        assert result == created
        assert is_new is True

    async def test_resolve_party_cached(
        self, service: ElectionImportService, mock_party_repo: AsyncMock
    ) -> None:
        """キャッシュから政党が返される（DBアクセスなし）."""
        party = PoliticalParty(name="自由民主党", id=1)
        mock_party_repo.get_by_name.return_value = party

        # 1回目: DBから取得
        await service.resolve_party("自由民主党")
        # 2回目: キャッシュから
        result, is_new = await service.resolve_party("自由民主党")

        assert result == party
        assert is_new is False
        mock_party_repo.get_by_name.assert_called_once()

    async def test_resolve_party_empty_name(
        self, service: ElectionImportService
    ) -> None:
        """空の政党名ではNoneを返す."""
        result, is_new = await service.resolve_party("")
        assert result is None
        assert is_new is False

    # --- match_politician ---

    async def test_match_politician_single(
        self, service: ElectionImportService, mock_politician_repo: AsyncMock
    ) -> None:
        """1件マッチでmatchedを返す."""
        pol = Politician(name="渡辺孝一", prefecture="北海道", district="", id=1)
        mock_politician_repo.search_by_normalized_name.return_value = [pol]

        result, status = await service.match_politician("渡辺 孝一", None)
        assert status == "matched"
        assert result == pol

    async def test_match_politician_not_found(
        self, service: ElectionImportService, mock_politician_repo: AsyncMock
    ) -> None:
        """0件でnot_foundを返す."""
        mock_politician_repo.search_by_normalized_name.return_value = []

        result, status = await service.match_politician("新人 候補", None)
        assert status == "not_found"
        assert result is None

    async def test_match_politician_ambiguous(
        self, service: ElectionImportService, mock_politician_repo: AsyncMock
    ) -> None:
        """複数件（絞り込み不可）でambiguousを返す."""
        p1 = Politician(
            name="田中太郎", prefecture="", district="", political_party_id=1, id=10
        )
        p2 = Politician(
            name="田中太郎", prefecture="", district="", political_party_id=2, id=20
        )
        mock_politician_repo.search_by_normalized_name.return_value = [p1, p2]

        result, status = await service.match_politician("田中太郎", None)
        assert status == "ambiguous"
        assert result is None

    async def test_match_politician_ambiguous_with_party_filter(
        self, service: ElectionImportService, mock_politician_repo: AsyncMock
    ) -> None:
        """同姓同名で政党絞り込みにより1件になる場合matchedを返す."""
        p1 = Politician(
            name="田中太郎", prefecture="", district="", political_party_id=1, id=10
        )
        p2 = Politician(
            name="田中太郎", prefecture="", district="", political_party_id=2, id=20
        )
        mock_politician_repo.search_by_normalized_name.return_value = [p1, p2]

        result, status = await service.match_politician("田中太郎", 1)
        assert status == "matched"
        assert result == p1

    # --- create_politician ---

    async def test_create_politician_success(
        self, service: ElectionImportService, mock_politician_repo: AsyncMock
    ) -> None:
        """政治家の作成が成功する."""
        created = Politician(name="佐藤 花子", prefecture="", district="北海道", id=1)
        mock_politician_repo.create.return_value = created

        result = await service.create_politician("佐藤 花子", "", "北海道", 1)
        assert result == created

    async def test_create_politician_failure(
        self, service: ElectionImportService, mock_politician_repo: AsyncMock
    ) -> None:
        """政治家の作成が失敗した場合Noneを返す."""
        mock_politician_repo.create.side_effect = Exception("DB error")

        result = await service.create_politician("失敗 太郎", "", "", None)
        assert result is None

    # --- clear_cache ---

    async def test_clear_cache(
        self, service: ElectionImportService, mock_party_repo: AsyncMock
    ) -> None:
        """キャッシュがクリアされる."""
        party = PoliticalParty(name="自由民主党", id=1)
        mock_party_repo.get_by_name.return_value = party

        await service.resolve_party("自由民主党")
        assert len(service._party_cache) == 1

        service.clear_cache()
        assert len(service._party_cache) == 0


class TestGetOrCreateElection:
    """get_or_create_electionのテスト."""

    @pytest.fixture()
    def mock_election_repo(self) -> AsyncMock:
        return AsyncMock(spec=ElectionRepository)

    @pytest.fixture()
    def service(self, mock_election_repo: AsyncMock) -> ElectionImportService:
        return ElectionImportService(
            politician_repository=AsyncMock(spec=PoliticianRepository),
            political_party_repository=AsyncMock(spec=PoliticalPartyRepository),
            election_repository=mock_election_repo,
        )

    async def test_returns_existing_election(
        self, service: ElectionImportService, mock_election_repo: AsyncMock
    ) -> None:
        """既存Electionが存在する場合はそれを返す."""
        existing = Election(
            governing_body_id=1,
            term_number=50,
            election_date=date(2024, 10, 27),
            id=1,
        )
        mock_election_repo.get_by_governing_body_and_term.return_value = existing

        result = await service.get_or_create_election(1, 50, date(2024, 10, 27))
        assert result == existing
        mock_election_repo.create.assert_not_called()

    async def test_creates_new_election(
        self, service: ElectionImportService, mock_election_repo: AsyncMock
    ) -> None:
        """既存Electionがない場合は新規作成する."""
        mock_election_repo.get_by_governing_body_and_term.return_value = None
        created = Election(
            governing_body_id=1,
            term_number=50,
            election_date=date(2024, 10, 27),
            election_type=Election.ELECTION_TYPE_GENERAL,
            id=1,
        )
        mock_election_repo.create.return_value = created

        result = await service.get_or_create_election(1, 50, date(2024, 10, 27))
        assert result == created
        mock_election_repo.create.assert_called_once()

    async def test_returns_none_when_no_date(
        self, service: ElectionImportService, mock_election_repo: AsyncMock
    ) -> None:
        """election_dateがNoneで既存Electionもない場合はNoneを返す."""
        mock_election_repo.get_by_governing_body_and_term.return_value = None

        result = await service.get_or_create_election(1, 50, None)
        assert result is None
        mock_election_repo.create.assert_not_called()

    async def test_raises_when_no_election_repo(self) -> None:
        """election_repositoryが未設定の場合はRuntimeErrorを送出する."""
        service = ElectionImportService(
            politician_repository=AsyncMock(spec=PoliticianRepository),
            political_party_repository=AsyncMock(spec=PoliticalPartyRepository),
        )
        with pytest.raises(RuntimeError, match="election_repository is not set"):
            await service.get_or_create_election(1, 50, date(2024, 10, 27))
