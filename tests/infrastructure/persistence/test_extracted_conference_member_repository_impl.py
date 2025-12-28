"""Tests for ExtractedConferenceMemberRepositoryImpl."""

from unittest.mock import AsyncMock, MagicMock

import pytest

from sqlalchemy.ext.asyncio import AsyncSession

from src.domain.entities.extracted_conference_member import ExtractedConferenceMember
from src.infrastructure.persistence.extracted_conference_member_repository_impl import (
    ExtractedConferenceMemberModel,
    ExtractedConferenceMemberRepositoryImpl,
)


class TestExtractedConferenceMemberRepositoryImpl:
    """Test cases for ExtractedConferenceMemberRepositoryImpl."""

    @pytest.fixture
    def mock_session(self) -> MagicMock:
        """Create mock async session."""
        session = MagicMock(spec=AsyncSession)
        session.execute = AsyncMock()
        session.commit = AsyncMock()
        session.rollback = AsyncMock()
        return session

    @pytest.fixture
    def repository(
        self, mock_session: MagicMock
    ) -> ExtractedConferenceMemberRepositoryImpl:
        """Create extracted conference member repository."""
        return ExtractedConferenceMemberRepositoryImpl(mock_session)

    @pytest.fixture
    def sample_member_entity(self) -> ExtractedConferenceMember:
        """Sample extracted conference member entity."""
        return ExtractedConferenceMember(
            id=1,
            conference_id=10,
            extracted_name="山田太郎",
            source_url="https://example.com/member",
            extracted_party_name="自民党",
            matching_status="pending",
            matched_politician_id=None,
        )

    @pytest.mark.asyncio
    async def test_get_pending_members(
        self,
        repository: ExtractedConferenceMemberRepositoryImpl,
        mock_session: MagicMock,
    ) -> None:
        """Test get_pending_members returns pending members."""
        mock_row = MagicMock()
        mock_row.id = 1
        mock_row.conference_id = 10
        mock_row.extracted_name = "山田太郎"
        mock_row.source_url = "https://example.com/member"
        mock_row.extracted_role = "議員"
        mock_row.extracted_party_name = "自民党"
        mock_row.extracted_at = None
        mock_row.matching_status = "pending"
        mock_row.matched_politician_id = None
        mock_row.matching_confidence = None
        mock_row.matched_at = None
        mock_row.additional_data = None

        mock_result = MagicMock()
        mock_result.fetchall = MagicMock(return_value=[mock_row])
        mock_session.execute.return_value = mock_result

        result = await repository.get_pending_members(10)

        assert len(result) == 1
        assert result[0].matching_status == "pending"
        mock_session.execute.assert_called_once()

    @pytest.mark.asyncio
    async def test_get_matched_members(
        self,
        repository: ExtractedConferenceMemberRepositoryImpl,
        mock_session: MagicMock,
    ) -> None:
        """Test get_matched_members returns matched members."""
        mock_row = MagicMock()
        mock_row.id = 1
        mock_row.conference_id = 10
        mock_row.extracted_name = "山田太郎"
        mock_row.source_url = "https://example.com/member"
        mock_row.extracted_role = "議員"
        mock_row.extracted_party_name = "自民党"
        mock_row.extracted_at = None
        mock_row.matching_status = "matched"
        mock_row.matched_politician_id = 100
        mock_row.matching_confidence = 0.95
        mock_row.matched_at = None
        mock_row.additional_data = None

        mock_result = MagicMock()
        mock_result.fetchall = MagicMock(return_value=[mock_row])
        mock_session.execute.return_value = mock_result

        result = await repository.get_matched_members(10)

        assert len(result) == 1
        assert result[0].matched_politician_id == 100
        mock_session.execute.assert_called_once()

    @pytest.mark.asyncio
    async def test_update_matching_result_success(
        self,
        repository: ExtractedConferenceMemberRepositoryImpl,
        mock_session: MagicMock,
    ) -> None:
        """Test update_matching_result successfully updates result."""
        # Mock for update query
        mock_update_result = MagicMock()

        # Mock for get_by_id query
        mock_row = MagicMock()
        mock_row.id = 1
        mock_row.conference_id = 10
        mock_row.extracted_name = "山田太郎"
        mock_row.source_url = "https://example.com/member"
        mock_row.extracted_role = "議員"
        mock_row.extracted_party_name = "自民党"
        mock_row.extracted_at = None
        mock_row.matched_politician_id = 100
        mock_row.matching_confidence = 0.95
        mock_row.matching_status = "matched"
        mock_row.matched_at = None
        mock_row.additional_data = None

        mock_get_result = MagicMock()
        mock_get_result.fetchone = MagicMock(return_value=mock_row)

        mock_session.execute.side_effect = [mock_update_result, mock_get_result]

        result = await repository.update_matching_result(1, 100, 0.95, "matched")

        assert result is not None
        assert result.matched_politician_id == 100
        assert mock_session.execute.call_count == 2
        mock_session.commit.assert_called_once()

    @pytest.mark.asyncio
    async def test_update_matching_result_not_found(
        self,
        repository: ExtractedConferenceMemberRepositoryImpl,
        mock_session: MagicMock,
    ) -> None:
        """Test update_matching_result returns None when not found."""
        # Mock for update query
        mock_update_result = MagicMock()

        # Mock for get_by_id query (returns None)
        mock_get_result = MagicMock()
        mock_get_result.fetchone = MagicMock(return_value=None)

        mock_session.execute.side_effect = [mock_update_result, mock_get_result]

        result = await repository.update_matching_result(999, 100, 0.95, "matched")

        assert result is None
        mock_session.commit.assert_called_once()

    @pytest.mark.asyncio
    async def test_get_by_conference(
        self,
        repository: ExtractedConferenceMemberRepositoryImpl,
        mock_session: MagicMock,
    ) -> None:
        """Test get_by_conference returns members for conference."""
        mock_row = MagicMock()
        mock_row.id = 1
        mock_row.conference_id = 10
        mock_row.extracted_name = "山田太郎"
        mock_row.source_url = "https://example.com/member"
        mock_row.extracted_role = "議員"
        mock_row.extracted_party_name = None
        mock_row.extracted_at = None
        mock_row.matching_status = "pending"
        mock_row.matched_politician_id = None
        mock_row.matching_confidence = None
        mock_row.matched_at = None
        mock_row.additional_data = None

        mock_result = MagicMock()
        mock_result.fetchall = MagicMock(return_value=[mock_row])
        mock_session.execute.return_value = mock_result

        result = await repository.get_by_conference(10)

        assert len(result) == 1
        assert result[0].conference_id == 10
        mock_session.execute.assert_called_once()

    @pytest.mark.asyncio
    async def test_get_extraction_summary(
        self,
        repository: ExtractedConferenceMemberRepositoryImpl,
        mock_session: MagicMock,
    ) -> None:
        """Test get_extraction_summary returns summary dict."""
        # Mock rows returned by SQL query
        mock_row1 = MagicMock()
        mock_row1.matching_status = "pending"
        mock_row1.count = 20

        mock_row2 = MagicMock()
        mock_row2.matching_status = "matched"
        mock_row2.count = 80

        mock_result = MagicMock()
        mock_result.fetchall = MagicMock(return_value=[mock_row1, mock_row2])
        mock_session.execute.return_value = mock_result

        result = await repository.get_extraction_summary()

        # Result should be a dict
        assert isinstance(result, dict)
        assert result["total"] == 100
        assert result["pending"] == 20
        assert result["matched"] == 80
        mock_session.execute.assert_called_once()

    @pytest.mark.asyncio
    async def test_bulk_create(
        self,
        repository: ExtractedConferenceMemberRepositoryImpl,
        mock_session: MagicMock,
        sample_member_entity: ExtractedConferenceMember,
    ) -> None:
        """Test bulk_create creates multiple members."""
        # Mock session methods
        mock_session.add_all = MagicMock()
        mock_session.refresh = AsyncMock()

        result = await repository.bulk_create([sample_member_entity])

        # Result should be a list of entities
        assert isinstance(result, list)
        assert len(result) == 1
        mock_session.add_all.assert_called_once()
        mock_session.commit.assert_called_once()

    def test_to_entity(
        self, repository: ExtractedConferenceMemberRepositoryImpl
    ) -> None:
        """Test _to_entity converts model to entity correctly."""
        model = ExtractedConferenceMemberModel(
            id=1,
            conference_id=10,
            extracted_name="山田太郎",
            source_url="https://example.com/member",
            extracted_role="議員",
            extracted_party_name="自民党",
            extracted_at=None,
            matched_politician_id=None,
            matching_confidence=None,
            matching_status="pending",
            matched_at=None,
        )

        entity = repository._to_entity(model)

        assert isinstance(entity, ExtractedConferenceMember)
        assert entity.id == 1
        assert entity.extracted_name == "山田太郎"

    def test_to_model(
        self,
        repository: ExtractedConferenceMemberRepositoryImpl,
        sample_member_entity: ExtractedConferenceMember,
    ) -> None:
        """Test _to_model converts entity to model correctly."""
        model = repository._to_model(sample_member_entity)

        assert isinstance(model, ExtractedConferenceMemberModel)
        assert model.conference_id == 10
        assert model.extracted_name == "山田太郎"
