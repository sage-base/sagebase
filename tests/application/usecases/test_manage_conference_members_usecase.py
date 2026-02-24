"""Tests for ManageConferenceMembersUseCase."""

from datetime import date
from unittest.mock import AsyncMock

import pytest

from src.application.usecases.manage_conference_members_usecase import (
    GetElectionCandidatesInputDTO,
    ManageConferenceMembersUseCase,
    ManualMatchInputDTO,
)
from src.domain.entities.conference import Conference
from src.domain.entities.conference_member import ConferenceMember
from src.domain.entities.election_member import ElectionMember
from src.domain.entities.politician import Politician


class TestManageConferenceMembersUseCase:
    """Test cases for ManageConferenceMembersUseCase."""

    @pytest.fixture
    def mock_conference_repo(self) -> AsyncMock:
        """Create mock conference repository."""
        repo = AsyncMock()
        repo.get_by_id.return_value = Conference(
            id=1,
            governing_body_id=1,
            name="Test Conference",
        )
        return repo

    @pytest.fixture
    def mock_politician_repo(self) -> AsyncMock:
        """Create mock politician repository."""
        repo = AsyncMock()
        repo.get_all.return_value = []
        repo.get_by_id.return_value = None
        repo.search_by_name.return_value = []
        return repo

    @pytest.fixture
    def mock_conference_member_repo(self) -> AsyncMock:
        """Create mock conference member repository."""
        repo = AsyncMock()
        return repo

    @pytest.fixture
    def usecase(
        self,
        mock_conference_repo: AsyncMock,
        mock_politician_repo: AsyncMock,
        mock_conference_member_repo: AsyncMock,
    ) -> ManageConferenceMembersUseCase:
        """Create use case instance with mocks."""
        return ManageConferenceMembersUseCase(
            conference_repository=mock_conference_repo,
            politician_repository=mock_politician_repo,
            conference_member_repository=mock_conference_member_repo,
        )

    @pytest.mark.asyncio
    async def test_manual_match_success(
        self,
        usecase,
        mock_politician_repo,
        mock_conference_member_repo,
    ):
        """Test successful manual match creating ConferenceMember."""
        politician = Politician(
            id=10,
            name="山田太郎",
            prefecture="東京都",
            district="東京1区",
        )
        mock_politician_repo.get_by_id.return_value = politician

        mock_conference_member_repo.get_by_politician_and_conference.return_value = []
        mock_conference_member_repo.create.return_value = ConferenceMember(
            id=1,
            politician_id=10,
            conference_id=1,
            role="議員",
            start_date=date.today(),
        )

        request = ManualMatchInputDTO(politician_id=10, conference_id=1)
        result = await usecase.manual_match(request)

        assert result.success is True
        assert "完了" in result.message

        # Gold Layer（ConferenceMember）が作成されることを確認
        mock_conference_member_repo.create.assert_called_once()

    @pytest.mark.asyncio
    async def test_manual_match_politician_not_found(
        self, usecase, mock_politician_repo
    ):
        """Test manual match when politician not found."""
        mock_politician_repo.get_by_id.return_value = None

        request = ManualMatchInputDTO(politician_id=999, conference_id=1)
        result = await usecase.manual_match(request)

        assert result.success is False
        assert "見つかりません" in result.message

    @pytest.mark.asyncio
    async def test_manual_match_skip_existing_affiliation(
        self,
        usecase,
        mock_politician_repo,
        mock_conference_repo,
        mock_conference_member_repo,
    ):
        """Test manual match skips creation when active affiliation exists."""
        politician = Politician(
            id=10,
            name="山田太郎",
            prefecture="東京都",
            district="東京1区",
        )
        mock_politician_repo.get_by_id.return_value = politician

        conference = Conference(
            id=1,
            name="Test Conference",
            governing_body_id=1,
        )
        mock_conference_repo.get_by_id.return_value = conference

        # Existing active affiliation
        existing_affiliation = ConferenceMember(
            id=100,
            politician_id=10,
            conference_id=1,
            role="議員",
            start_date=date(2023, 1, 1),
            end_date=None,  # Active
        )
        mock_conference_member_repo.get_by_politician_and_conference.return_value = [
            existing_affiliation
        ]

        request = ManualMatchInputDTO(politician_id=10, conference_id=1)
        result = await usecase.manual_match(request)

        assert result.success is True
        # Should not create new affiliation
        mock_conference_member_repo.upsert.assert_not_called()

    @pytest.mark.asyncio
    async def test_search_politicians(self, usecase, mock_politician_repo):
        """Test politician search functionality."""
        from src.application.usecases.manage_conference_members_usecase import (
            SearchPoliticiansInputDTO,
        )

        mock_politician_repo.search_by_name.return_value = [
            Politician(
                id=10,
                name="山田太郎",
                prefecture="東京都",
                district="東京1区",
            )
        ]

        request = SearchPoliticiansInputDTO(name="山田太郎")
        result = await usecase.search_politicians(request)

        assert len(result.candidates) == 1
        assert result.candidates[0].name == "山田太郎"
        assert result.candidates[0].id == 10

    @pytest.mark.asyncio
    async def test_search_politicians_empty_name(self, usecase, mock_politician_repo):
        """Test politician search with empty name."""
        from src.application.usecases.manage_conference_members_usecase import (
            SearchPoliticiansInputDTO,
        )

        request = SearchPoliticiansInputDTO(name="")
        result = await usecase.search_politicians(request)

        assert len(result.candidates) == 0
        mock_politician_repo.search_by_name.assert_not_called()


class TestGetElectionCandidates:
    """get_election_candidatesメソッドのテスト."""

    @pytest.fixture
    def mock_conference_repo(self) -> AsyncMock:
        repo = AsyncMock()
        repo.get_by_id.return_value = Conference(
            id=1,
            governing_body_id=1,
            name="Test Conference",
            election_id=10,
        )
        return repo

    @pytest.fixture
    def mock_politician_repo(self) -> AsyncMock:
        repo = AsyncMock()
        return repo

    @pytest.fixture
    def mock_election_member_repo(self) -> AsyncMock:
        repo = AsyncMock()
        return repo

    @pytest.fixture
    def mock_conference_member_repo(self) -> AsyncMock:
        return AsyncMock()

    @pytest.fixture
    def usecase(
        self,
        mock_conference_repo,
        mock_politician_repo,
        mock_conference_member_repo,
        mock_election_member_repo,
    ) -> ManageConferenceMembersUseCase:
        return ManageConferenceMembersUseCase(
            conference_repository=mock_conference_repo,
            politician_repository=mock_politician_repo,
            conference_member_repository=mock_conference_member_repo,
            election_member_repository=mock_election_member_repo,
        )

    @pytest.mark.asyncio
    async def test_get_election_candidates_success(
        self,
        usecase,
        mock_conference_repo,
        mock_election_member_repo,
        mock_politician_repo,
    ):
        """当選者一覧を正常に取得できること."""
        mock_election_member_repo.get_by_election_id.return_value = [
            ElectionMember(
                id=1, election_id=10, politician_id=100, result="当選", votes=5000
            ),
            ElectionMember(
                id=2, election_id=10, politician_id=200, result="当選", votes=4000
            ),
            ElectionMember(
                id=3, election_id=10, politician_id=300, result="落選", votes=1000
            ),
        ]
        mock_politician_repo.get_by_id.side_effect = [
            Politician(
                id=100, name="山田太郎", prefecture="東京都", district="東京1区"
            ),
            Politician(
                id=200, name="佐藤花子", prefecture="東京都", district="東京2区"
            ),
        ]

        request = GetElectionCandidatesInputDTO(conference_id=1)
        result = await usecase.get_election_candidates(request)

        assert len(result.candidates) == 2
        assert result.candidates[0].name == "山田太郎"
        assert result.candidates[0].id == 100
        assert result.candidates[1].name == "佐藤花子"
        assert result.candidates[1].id == 200
        mock_conference_repo.get_by_id.assert_called_once_with(1)
        mock_election_member_repo.get_by_election_id.assert_called_once_with(10)
        assert mock_politician_repo.get_by_id.call_count == 2

    @pytest.mark.asyncio
    async def test_get_election_candidates_no_election_id(
        self, usecase, mock_conference_repo
    ):
        """election_idが未設定の場合、空リストを返すこと."""
        mock_conference_repo.get_by_id.return_value = Conference(
            id=1,
            governing_body_id=1,
            name="Test Conference",
            election_id=None,
        )

        request = GetElectionCandidatesInputDTO(conference_id=1)
        result = await usecase.get_election_candidates(request)

        assert len(result.candidates) == 0

    @pytest.mark.asyncio
    async def test_get_election_candidates_conference_not_found(
        self, usecase, mock_conference_repo
    ):
        """会議体が見つからない場合、空リストを返すこと."""
        mock_conference_repo.get_by_id.return_value = None

        request = GetElectionCandidatesInputDTO(conference_id=999)
        result = await usecase.get_election_candidates(request)

        assert len(result.candidates) == 0

    @pytest.mark.asyncio
    async def test_get_election_candidates_no_elected_members(
        self,
        usecase,
        mock_election_member_repo,
    ):
        """当選者が0件の場合、空リストを返すこと."""
        mock_election_member_repo.get_by_election_id.return_value = [
            ElectionMember(
                id=1, election_id=10, politician_id=100, result="落選", votes=1000
            ),
        ]

        request = GetElectionCandidatesInputDTO(conference_id=1)
        result = await usecase.get_election_candidates(request)

        assert len(result.candidates) == 0

    @pytest.mark.asyncio
    async def test_get_election_candidates_no_election_member_repo(
        self,
        mock_conference_repo,
        mock_politician_repo,
        mock_conference_member_repo,
    ):
        """election_member_repoが未設定の場合、空リストを返すこと."""
        usecase = ManageConferenceMembersUseCase(
            conference_repository=mock_conference_repo,
            politician_repository=mock_politician_repo,
            conference_member_repository=mock_conference_member_repo,
        )

        request = GetElectionCandidatesInputDTO(conference_id=1)
        result = await usecase.get_election_candidates(request)

        assert len(result.candidates) == 0

    @pytest.mark.asyncio
    async def test_get_election_candidates_includes_special_elected(
        self,
        usecase,
        mock_election_member_repo,
        mock_politician_repo,
    ):
        """繰上当選・無投票当選も当選者として含まれること."""
        mock_election_member_repo.get_by_election_id.return_value = [
            ElectionMember(
                id=1,
                election_id=10,
                politician_id=100,
                result="繰上当選",
                votes=0,
            ),
            ElectionMember(
                id=2,
                election_id=10,
                politician_id=200,
                result="無投票当選",
                votes=0,
            ),
            ElectionMember(
                id=3,
                election_id=10,
                politician_id=300,
                result="落選",
                votes=1000,
            ),
            ElectionMember(
                id=4,
                election_id=10,
                politician_id=400,
                result="次点",
                votes=2000,
            ),
        ]
        mock_politician_repo.get_by_id.side_effect = [
            Politician(
                id=100, name="田中三郎", prefecture="東京都", district="東京1区"
            ),
            Politician(
                id=200, name="高橋四郎", prefecture="東京都", district="東京2区"
            ),
        ]

        request = GetElectionCandidatesInputDTO(conference_id=1)
        result = await usecase.get_election_candidates(request)

        assert len(result.candidates) == 2
        assert result.candidates[0].name == "田中三郎"
        assert result.candidates[1].name == "高橋四郎"

    @pytest.mark.asyncio
    async def test_get_election_candidates_skips_missing_politician(
        self,
        usecase,
        mock_election_member_repo,
        mock_politician_repo,
    ):
        """政治家が見つからない当選者はスキップされること."""
        mock_election_member_repo.get_by_election_id.return_value = [
            ElectionMember(
                id=1,
                election_id=10,
                politician_id=100,
                result="当選",
                votes=5000,
            ),
            ElectionMember(
                id=2,
                election_id=10,
                politician_id=200,
                result="当選",
                votes=4000,
            ),
        ]
        mock_politician_repo.get_by_id.side_effect = [
            Politician(
                id=100, name="山田太郎", prefecture="東京都", district="東京1区"
            ),
            None,
        ]

        request = GetElectionCandidatesInputDTO(conference_id=1)
        result = await usecase.get_election_candidates(request)

        assert len(result.candidates) == 1
        assert result.candidates[0].id == 100
        assert result.candidates[0].name == "山田太郎"
