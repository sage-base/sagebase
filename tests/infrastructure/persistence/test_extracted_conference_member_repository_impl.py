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
    """Test cases for ExtractedConferenceMemberRepositoryImpl.

    Bronze Layer（抽出ログ層）のリポジトリテスト。
    政治家との紐付け機能はGold Layer（ConferenceMemberRepository）に移行済み。
    """

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
        )

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
        """Test get_extraction_summary returns summary dict with total count."""
        mock_row = MagicMock()
        mock_row.total = 100

        mock_result = MagicMock()
        mock_result.fetchone = MagicMock(return_value=mock_row)
        mock_session.execute.return_value = mock_result

        result = await repository.get_extraction_summary()

        assert isinstance(result, dict)
        assert result["total"] == 100
        mock_session.execute.assert_called_once()

    @pytest.mark.asyncio
    async def test_get_extraction_summary_with_conference_id(
        self,
        repository: ExtractedConferenceMemberRepositoryImpl,
        mock_session: MagicMock,
    ) -> None:
        """Test get_extraction_summary with conference_id filter."""
        mock_row = MagicMock()
        mock_row.total = 50

        mock_result = MagicMock()
        mock_result.fetchone = MagicMock(return_value=mock_row)
        mock_session.execute.return_value = mock_result

        result = await repository.get_extraction_summary(conference_id=10)

        assert result["total"] == 50
        mock_session.execute.assert_called_once()

    @pytest.mark.asyncio
    async def test_bulk_create(
        self,
        repository: ExtractedConferenceMemberRepositoryImpl,
        mock_session: MagicMock,
        sample_member_entity: ExtractedConferenceMember,
    ) -> None:
        """Test bulk_create creates multiple members."""
        mock_session.add_all = MagicMock()
        mock_session.refresh = AsyncMock()

        result = await repository.bulk_create([sample_member_entity])

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

    @pytest.mark.asyncio
    async def test_get_all_returns_members(
        self,
        repository: ExtractedConferenceMemberRepositoryImpl,
        mock_session: MagicMock,
    ) -> None:
        """Test get_all returns all members."""
        mock_row1 = MagicMock()
        mock_row1.id = 1
        mock_row1.conference_id = 10
        mock_row1.extracted_name = "山田太郎"
        mock_row1.source_url = "https://example.com/member1"
        mock_row1.extracted_at = None

        mock_row2 = MagicMock()
        mock_row2.id = 2
        mock_row2.conference_id = 10
        mock_row2.extracted_name = "鈴木花子"
        mock_row2.source_url = "https://example.com/member2"
        mock_row2.extracted_at = None

        mock_result = MagicMock()
        mock_result.fetchall = MagicMock(return_value=[mock_row1, mock_row2])
        mock_session.execute.return_value = mock_result

        result = await repository.get_all()

        assert len(result) == 2
        assert result[0].extracted_name == "山田太郎"
        assert result[1].extracted_name == "鈴木花子"
        mock_session.execute.assert_called_once()

    @pytest.mark.asyncio
    async def test_get_all_with_limit_offset(
        self,
        repository: ExtractedConferenceMemberRepositoryImpl,
        mock_session: MagicMock,
    ) -> None:
        """Test get_all with limit and offset parameters."""
        mock_row = MagicMock()
        mock_row.id = 1
        mock_row.conference_id = 10
        mock_row.extracted_name = "山田太郎"
        mock_row.source_url = "https://example.com/member"
        mock_row.extracted_at = None

        mock_result = MagicMock()
        mock_result.fetchall = MagicMock(return_value=[mock_row])
        mock_session.execute.return_value = mock_result

        result = await repository.get_all(limit=10, offset=5)

        assert len(result) == 1
        mock_session.execute.assert_called_once()

    @pytest.mark.asyncio
    async def test_get_all_empty(
        self,
        repository: ExtractedConferenceMemberRepositoryImpl,
        mock_session: MagicMock,
    ) -> None:
        """Test get_all returns empty list when no members exist."""
        mock_result = MagicMock()
        mock_result.fetchall = MagicMock(return_value=[])
        mock_session.execute.return_value = mock_result

        result = await repository.get_all()

        assert result == []
        mock_session.execute.assert_called_once()

    @pytest.mark.asyncio
    async def test_create_success(
        self,
        repository: ExtractedConferenceMemberRepositoryImpl,
        mock_session: MagicMock,
        sample_member_entity: ExtractedConferenceMember,
    ) -> None:
        """Test create successfully creates member."""
        mock_row = MagicMock()
        mock_row.id = 1

        mock_result = MagicMock()
        mock_result.fetchone = MagicMock(return_value=mock_row)
        mock_session.execute.return_value = mock_result

        result = await repository.create(sample_member_entity)

        assert result.id == 1
        assert result.extracted_name == "山田太郎"
        mock_session.execute.assert_called_once()
        mock_session.commit.assert_called_once()

    @pytest.mark.asyncio
    async def test_update_success(
        self,
        repository: ExtractedConferenceMemberRepositoryImpl,
        mock_session: MagicMock,
        sample_member_entity: ExtractedConferenceMember,
    ) -> None:
        """Test update successfully updates member."""
        mock_result = MagicMock()
        mock_session.execute.return_value = mock_result

        sample_member_entity.extracted_name = "山田太郎（更新）"
        result = await repository.update(sample_member_entity)

        assert result.extracted_name == "山田太郎（更新）"
        mock_session.execute.assert_called_once()
        mock_session.commit.assert_called_once()

    @pytest.mark.asyncio
    async def test_update_without_id(
        self,
        repository: ExtractedConferenceMemberRepositoryImpl,
        mock_session: MagicMock,
    ) -> None:
        """Test update raises ValueError when entity has no ID."""
        entity = ExtractedConferenceMember(
            conference_id=10,
            extracted_name="山田太郎",
            source_url="https://example.com/member",
        )

        with pytest.raises(ValueError, match="Entity must have an ID to update"):
            await repository.update(entity)

    @pytest.mark.asyncio
    async def test_delete_success(
        self,
        repository: ExtractedConferenceMemberRepositoryImpl,
        mock_session: MagicMock,
    ) -> None:
        """Test delete successfully deletes member."""
        mock_result = MagicMock()
        mock_result.rowcount = 1
        mock_session.execute.return_value = mock_result

        result = await repository.delete(1)

        assert result is True
        mock_session.execute.assert_called_once()
        mock_session.commit.assert_called_once()

    @pytest.mark.asyncio
    async def test_delete_not_found(
        self,
        repository: ExtractedConferenceMemberRepositoryImpl,
        mock_session: MagicMock,
    ) -> None:
        """Test delete returns False when member not found."""
        mock_result = MagicMock()
        mock_result.rowcount = 0
        mock_session.execute.return_value = mock_result

        result = await repository.delete(999)

        assert result is False
        mock_session.execute.assert_called_once()

    @pytest.mark.asyncio
    async def test_count(
        self,
        repository: ExtractedConferenceMemberRepositoryImpl,
        mock_session: MagicMock,
    ) -> None:
        """Test count returns total number of members."""
        mock_result = MagicMock()
        mock_result.scalar = MagicMock(return_value=100)
        mock_session.execute.return_value = mock_result

        result = await repository.count()

        assert result == 100
        mock_session.execute.assert_called_once()

    @pytest.mark.asyncio
    async def test_count_zero(
        self,
        repository: ExtractedConferenceMemberRepositoryImpl,
        mock_session: MagicMock,
    ) -> None:
        """Test count returns 0 when no members exist."""
        mock_result = MagicMock()
        mock_result.scalar = MagicMock(return_value=0)
        mock_session.execute.return_value = mock_result

        result = await repository.count()

        assert result == 0
        mock_session.execute.assert_called_once()

    def test_update_model(
        self,
        repository: ExtractedConferenceMemberRepositoryImpl,
        sample_member_entity: ExtractedConferenceMember,
    ) -> None:
        """Test _update_model updates model fields from entity."""
        model = ExtractedConferenceMemberModel(
            id=1,
            conference_id=5,
            extracted_name="旧名前",
            source_url="https://old.com/member",
            extracted_at=None,
        )

        repository._update_model(model, sample_member_entity)

        assert model.conference_id == 10
        assert model.extracted_name == "山田太郎"
        assert model.source_url == "https://example.com/member"

    def test_to_model_with_additional_data(
        self, repository: ExtractedConferenceMemberRepositoryImpl
    ) -> None:
        """Test _to_model with additional_data."""
        entity = ExtractedConferenceMember(
            id=1,
            conference_id=10,
            extracted_name="山田太郎",
            source_url="https://example.com/member",
            additional_data='{"key": "value"}',
        )

        model = repository._to_model(entity)

        assert isinstance(model, ExtractedConferenceMemberModel)
        assert model.additional_data == '{"key": "value"}'
