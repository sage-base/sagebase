"""Tests for ManageConferenceMembersUseCase."""

from datetime import date
from typing import Any
from unittest.mock import AsyncMock, Mock

import pytest

from src.application.usecases.manage_conference_members_usecase import (
    ExtractedMemberDTO,
    ExtractMembersInputDTO,
    ManageConferenceMembersUseCase,
    ManualMatchInputDTO,
)
from src.domain.entities.conference import Conference
from src.domain.entities.conference_member import ConferenceMember
from src.domain.entities.politician import Politician


def create_mock_extracted_member(**kwargs: Any) -> Mock:
    """Helper to create a mock extracted member entity.

    Bronze Layer（抽出ログ層）のモックエンティティを作成。
    """
    member = Mock()
    member.id = kwargs.get("id", 1)
    member.extracted_name = kwargs.get("name", "Test Member")
    member.conference_id = kwargs.get("conference_id", 1)
    member.extracted_party_name = kwargs.get("party_affiliation", None)
    member.extracted_role = kwargs.get("role", None)
    member.is_manually_verified = kwargs.get("is_manually_verified", False)
    # For backward compatibility with some tests
    member.name = member.extracted_name
    member.party_affiliation = member.extracted_party_name
    member.role = member.extracted_role
    return member


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
            type="委員会",
            members_introduction_url="https://example.com/members",
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
    def mock_conference_service(self) -> Mock:
        """Create mock conference domain service."""
        service = Mock()
        service.extract_member_role.return_value = "議員"
        service.normalize_party_name.return_value = "自由民主党"
        service.calculate_member_confidence_score.return_value = 0.95
        service.calculate_affiliation_overlap.return_value = False
        return service

    @pytest.fixture
    def mock_extracted_repo(self) -> AsyncMock:
        """Create mock extracted member repository."""
        repo = AsyncMock()
        return repo

    @pytest.fixture
    def mock_conference_member_repo(self) -> AsyncMock:
        """Create mock conference member repository."""
        repo = AsyncMock()
        return repo

    @pytest.fixture
    def mock_scraper(self) -> AsyncMock:
        """Create mock web scraper service."""
        scraper = AsyncMock()
        scraper.scrape_conference_members.return_value = [
            {"name": "山田太郎", "party": "自由民主党", "role": "議員"},
            {"name": "佐藤花子", "party": "立憲民主党", "role": "委員長"},
        ]
        return scraper

    @pytest.fixture
    def usecase(
        self,
        mock_conference_repo: AsyncMock,
        mock_politician_repo: AsyncMock,
        mock_conference_service: Mock,
        mock_extracted_repo: AsyncMock,
        mock_conference_member_repo: AsyncMock,
        mock_scraper: AsyncMock,
    ) -> ManageConferenceMembersUseCase:
        """Create use case instance with mocks."""
        return ManageConferenceMembersUseCase(
            conference_repository=mock_conference_repo,
            politician_repository=mock_politician_repo,
            conference_domain_service=mock_conference_service,
            extracted_member_repository=mock_extracted_repo,
            conference_member_repository=mock_conference_member_repo,
            web_scraper_service=mock_scraper,
        )

    @pytest.mark.asyncio
    async def test_extract_members_success(
        self, usecase, mock_conference_repo, mock_extracted_repo, mock_scraper
    ):
        """Test successful member extraction."""
        mock_extracted_repo.get_by_conference.return_value = []

        mock_extracted_repo.create.side_effect = [
            create_mock_extracted_member(
                id=1,
                name="山田太郎",
                conference_id=1,
                party_affiliation="自由民主党",
                role="議員",
            ),
            create_mock_extracted_member(
                id=2,
                name="佐藤花子",
                conference_id=1,
                party_affiliation="立憲民主党",
                role="委員長",
            ),
        ]
        mock_scraper.scrape_conference_members.return_value = [
            {"name": "山田太郎", "party": "自由民主党", "role": "議員"},
            {"name": "佐藤花子", "party": "立憲民主党", "role": "委員長"},
        ]

        request = ExtractMembersInputDTO(conference_id=1, force=False)
        result = await usecase.extract_members(request)

        assert result.extracted_count == 2
        assert len(result.members) == 2
        assert result.members[0].name == "山田太郎"
        assert result.members[1].name == "佐藤花子"

        mock_conference_repo.get_by_id.assert_called_once_with(1)
        assert mock_extracted_repo.create.call_count == 2

    @pytest.mark.asyncio
    async def test_extract_members_no_url(self, usecase, mock_conference_repo):
        """Test extraction when conference has no members URL."""
        mock_conference_repo.get_by_id.return_value = Conference(
            id=1,
            governing_body_id=1,
            name="Test Conference",
            type="委員会",
            members_introduction_url=None,
        )

        with pytest.raises(ValueError, match="no members URL"):
            request = ExtractMembersInputDTO(conference_id=1, force=False)
            await usecase.extract_members(request)

    @pytest.mark.asyncio
    async def test_extract_members_already_extracted(
        self, usecase, mock_extracted_repo
    ):
        """Test extraction when members already exist and force=False."""
        existing_members = [
            create_mock_extracted_member(
                id=1,
                name="Existing Member",
                conference_id=1,
                party_affiliation="党名",
                role="役職",
            )
        ]
        mock_extracted_repo.get_by_conference.return_value = existing_members

        request = ExtractMembersInputDTO(conference_id=1, force=False)
        result = await usecase.extract_members(request)

        assert result.extracted_count == 1
        assert len(result.members) == 1
        assert result.members[0].name == "Existing Member"

    @pytest.mark.asyncio
    async def test_extract_members_force_re_extraction(
        self, usecase, mock_extracted_repo, mock_scraper
    ):
        """Test forced re-extraction of members."""
        mock_extracted_repo.get_by_conference.return_value = [
            create_mock_extracted_member(
                id=1,
                name="Old Member",
                conference_id=1,
                party_affiliation="党名",
                role="役職",
            )
        ]
        mock_extracted_repo.create.side_effect = [
            create_mock_extracted_member(
                id=2,
                name="山田太郎",
                conference_id=1,
                party_affiliation="自由民主党",
                role="議員",
            ),
            create_mock_extracted_member(
                id=3,
                name="佐藤花子",
                conference_id=1,
                party_affiliation="立憲民主党",
                role="委員長",
            ),
        ]
        mock_scraper.scrape_conference_members.return_value = [
            {"name": "山田太郎", "party": "自由民主党", "role": "議員"},
            {"name": "佐藤花子", "party": "立憲民主党", "role": "委員長"},
        ]

        request = ExtractMembersInputDTO(conference_id=1, force=True)
        result = await usecase.extract_members(request)

        assert result.extracted_count == 2
        assert len(result.members) == 2
        assert result.members[0].name == "山田太郎"
        assert result.members[1].name == "佐藤花子"

    @pytest.mark.asyncio
    async def test_manual_match_success(
        self,
        usecase,
        mock_extracted_repo,
        mock_politician_repo,
        mock_conference_member_repo,
    ):
        """Test successful manual match creating ConferenceMember."""
        member = create_mock_extracted_member(
            id=1,
            name="山田太郎",
            conference_id=1,
            role="議員",
        )
        mock_extracted_repo.get_by_id.return_value = member

        politician = Politician(
            id=10,
            name="山田太郎",
            prefecture="東京都",
            district="東京1区",
            political_party_id=1,
        )
        mock_politician_repo.get_by_id.return_value = politician

        mock_conference_member_repo.get_by_politician_and_conference.return_value = []
        mock_conference_member_repo.create.return_value = ConferenceMember(
            id=1,
            politician_id=10,
            conference_id=1,
            role="議員",
            start_date=date.today(),
            source_extracted_member_id=1,
        )

        request = ManualMatchInputDTO(member_id=1, politician_id=10)
        result = await usecase.manual_match(request)

        assert result.success is True
        assert result.member_id == 1
        assert "完了" in result.message

        # Gold Layer（ConferenceMember）が作成されることを確認
        mock_conference_member_repo.create.assert_called_once()

    @pytest.mark.asyncio
    async def test_manual_match_member_not_found(self, usecase, mock_extracted_repo):
        """Test manual match when member not found."""
        mock_extracted_repo.get_by_id.return_value = None

        request = ManualMatchInputDTO(member_id=999, politician_id=10)
        result = await usecase.manual_match(request)

        assert result.success is False
        assert "見つかりません" in result.message

    @pytest.mark.asyncio
    async def test_manual_match_politician_not_found(
        self, usecase, mock_extracted_repo, mock_politician_repo
    ):
        """Test manual match when politician not found."""
        member = create_mock_extracted_member(id=1, name="山田太郎")
        mock_extracted_repo.get_by_id.return_value = member
        mock_politician_repo.get_by_id.return_value = None

        request = ManualMatchInputDTO(member_id=1, politician_id=999)
        result = await usecase.manual_match(request)

        assert result.success is False
        assert "見つかりません" in result.message

    @pytest.mark.asyncio
    async def test_manual_match_skip_existing_affiliation(
        self,
        usecase,
        mock_extracted_repo,
        mock_politician_repo,
        mock_conference_member_repo,
    ):
        """Test manual match skips creation when active affiliation exists."""
        member = create_mock_extracted_member(
            id=1,
            name="山田太郎",
            conference_id=1,
        )
        mock_extracted_repo.get_by_id.return_value = member

        politician = Politician(
            id=10,
            name="山田太郎",
            prefecture="東京都",
            district="東京1区",
            political_party_id=1,
        )
        mock_politician_repo.get_by_id.return_value = politician

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

        request = ManualMatchInputDTO(member_id=1, politician_id=10)
        result = await usecase.manual_match(request)

        assert result.success is True
        # Should not create new affiliation
        mock_conference_member_repo.create.assert_not_called()

    @pytest.mark.asyncio
    async def test_to_extracted_dto(self, usecase):
        """Test conversion to ExtractedMemberDTO."""
        entity = create_mock_extracted_member(
            id=1,
            name="山田太郎",
            conference_id=1,
            party_affiliation="自由民主党",
            role="議員",
        )

        dto = usecase._to_extracted_dto(entity)

        assert isinstance(dto, ExtractedMemberDTO)
        assert dto.name == "山田太郎"
        assert dto.conference_id == 1
        assert dto.party_affiliation == "自由民主党"
        assert dto.role == "議員"

    @pytest.mark.asyncio
    async def test_error_handling_in_extract_members(
        self, usecase, mock_scraper, mock_extracted_repo
    ):
        """Test error handling during member extraction."""
        mock_extracted_repo.get_by_conference.return_value = []
        mock_scraper.scrape_conference_members.side_effect = Exception("Network error")

        with pytest.raises(Exception) as exc_info:
            request = ExtractMembersInputDTO(conference_id=1, force=False)
            await usecase.extract_members(request)

        assert "Network error" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_empty_extraction_result(
        self, usecase, mock_scraper, mock_extracted_repo
    ):
        """Test handling of empty extraction result."""
        mock_extracted_repo.get_by_conference.return_value = []
        mock_scraper.scrape_conference_members.return_value = []

        request = ExtractMembersInputDTO(conference_id=1, force=False)
        result = await usecase.extract_members(request)

        assert result.extracted_count == 0
        assert len(result.members) == 0

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
                political_party_id=1,
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
