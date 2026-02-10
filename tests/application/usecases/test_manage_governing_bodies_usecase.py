"""Tests for ManageGoverningBodiesUseCase."""

from unittest.mock import AsyncMock

import pytest

from src.application.usecases.manage_governing_bodies_usecase import (
    CreateGoverningBodyInputDto,
    CreateGoverningBodyOutputDto,
    DeleteGoverningBodyInputDto,
    DeleteGoverningBodyOutputDto,
    GoverningBodyListInputDto,
    GoverningBodyListOutputDto,
    ManageGoverningBodiesUseCase,
    UpdateGoverningBodyInputDto,
    UpdateGoverningBodyOutputDto,
)
from src.domain.entities.governing_body import GoverningBody


class TestManageGoverningBodiesUseCase:
    """Test cases for ManageGoverningBodiesUseCase."""

    @pytest.fixture
    def mock_governing_body_repository(self):
        """Create mock governing body repository."""
        repo = AsyncMock()
        return repo

    @pytest.fixture
    def use_case(self, mock_governing_body_repository):
        """Create ManageGoverningBodiesUseCase instance."""
        return ManageGoverningBodiesUseCase(
            governing_body_repository=mock_governing_body_repository
        )

    @pytest.mark.asyncio
    async def test_list_governing_bodies_success(
        self, use_case, mock_governing_body_repository
    ):
        """Test listing governing bodies successfully."""
        # Arrange
        governing_bodies = [
            GoverningBody(id=1, name="日本国", type="国"),
            GoverningBody(id=2, name="東京都", type="都道府県"),
            GoverningBody(id=3, name="横浜市", type="市町村"),
        ]
        mock_governing_body_repository.get_all.return_value = governing_bodies

        input_dto = GoverningBodyListInputDto()

        # Act
        result = await use_case.list_governing_bodies(input_dto)

        # Assert
        assert isinstance(result, GoverningBodyListOutputDto)
        assert len(result.governing_bodies) == 3
        assert result.statistics.total_count == 3
        assert result.statistics.country_count == 1
        assert result.statistics.prefecture_count == 1
        assert result.statistics.city_count == 1

    @pytest.mark.asyncio
    async def test_list_governing_bodies_filtered_by_type(
        self, use_case, mock_governing_body_repository
    ):
        """Test listing governing bodies filtered by type."""
        # Arrange
        all_bodies = [
            GoverningBody(id=1, name="日本国", type="国"),
            GoverningBody(id=2, name="東京都", type="都道府県"),
            GoverningBody(id=3, name="横浜市", type="市町村"),
        ]
        mock_governing_body_repository.get_all.return_value = all_bodies

        input_dto = GoverningBodyListInputDto(type_filter="都道府県")

        # Act
        result = await use_case.list_governing_bodies(input_dto)

        # Assert
        assert len(result.governing_bodies) == 1
        assert result.governing_bodies[0].type == "都道府県"
        assert result.statistics.total_count == 1

    @pytest.mark.asyncio
    async def test_list_governing_bodies_filtered_by_conference_exists(
        self, use_case, mock_governing_body_repository
    ):
        """Test listing governing bodies filtered by conference existence."""
        # Arrange
        body_with_conference = GoverningBody(id=1, name="東京都", type="都道府県")
        body_with_conference.conference_count = 5
        body_without_conference = GoverningBody(id=2, name="横浜市", type="市町村")
        body_without_conference.conference_count = 0

        all_bodies = [body_with_conference, body_without_conference]
        mock_governing_body_repository.get_all.return_value = all_bodies

        input_dto = GoverningBodyListInputDto(conference_filter="会議体あり")

        # Act
        result = await use_case.list_governing_bodies(input_dto)

        # Assert
        assert len(result.governing_bodies) == 1
        assert result.governing_bodies[0].id == 1

    @pytest.mark.asyncio
    async def test_list_governing_bodies_filtered_by_no_conference(
        self, use_case, mock_governing_body_repository
    ):
        """Test listing governing bodies filtered by no conference."""
        # Arrange
        body_with_conference = GoverningBody(id=1, name="東京都", type="都道府県")
        body_with_conference.conference_count = 5
        body_without_conference = GoverningBody(id=2, name="横浜市", type="市町村")
        body_without_conference.conference_count = 0

        all_bodies = [body_with_conference, body_without_conference]
        mock_governing_body_repository.get_all.return_value = all_bodies

        input_dto = GoverningBodyListInputDto(conference_filter="会議体なし")

        # Act
        result = await use_case.list_governing_bodies(input_dto)

        # Assert
        assert len(result.governing_bodies) == 1
        assert result.governing_bodies[0].id == 2

    @pytest.mark.asyncio
    async def test_list_governing_bodies_empty(
        self, use_case, mock_governing_body_repository
    ):
        """Test listing governing bodies when no bodies exist."""
        # Arrange
        mock_governing_body_repository.get_all.return_value = []

        input_dto = GoverningBodyListInputDto()

        # Act
        result = await use_case.list_governing_bodies(input_dto)

        # Assert
        assert len(result.governing_bodies) == 0
        assert result.statistics.total_count == 0

    @pytest.mark.asyncio
    async def test_create_governing_body_success(
        self, use_case, mock_governing_body_repository
    ):
        """Test creating a governing body successfully."""
        # Arrange
        mock_governing_body_repository.get_by_name_and_type.return_value = None
        created_body = GoverningBody(
            id=1,
            name="神奈川県",
            type="都道府県",
            organization_code="140007",
            organization_type="prefecture",
        )
        mock_governing_body_repository.create.return_value = created_body

        input_dto = CreateGoverningBodyInputDto(
            name="神奈川県",
            type="都道府県",
            organization_code="140007",
            organization_type="prefecture",
        )

        # Act
        result = await use_case.create_governing_body(input_dto)

        # Assert
        assert isinstance(result, CreateGoverningBodyOutputDto)
        assert result.success is True
        assert result.governing_body_id == 1
        mock_governing_body_repository.create.assert_called_once()

    @pytest.mark.asyncio
    async def test_create_governing_body_duplicate_error(
        self, use_case, mock_governing_body_repository
    ):
        """Test creating a governing body with duplicate name and type."""
        # Arrange
        existing_body = GoverningBody(id=1, name="東京都", type="都道府県")
        mock_governing_body_repository.get_by_name_and_type.return_value = existing_body

        input_dto = CreateGoverningBodyInputDto(name="東京都", type="都道府県")

        # Act
        result = await use_case.create_governing_body(input_dto)

        # Assert
        assert result.success is False
        assert "既に存在します" in result.error_message
        mock_governing_body_repository.create.assert_not_called()

    @pytest.mark.asyncio
    async def test_create_governing_body_repository_error(
        self, use_case, mock_governing_body_repository
    ):
        """Test creating a governing body with repository error."""
        # Arrange
        mock_governing_body_repository.get_by_name_and_type.return_value = None
        mock_governing_body_repository.create.side_effect = Exception("Database error")

        input_dto = CreateGoverningBodyInputDto(name="埼玉県", type="都道府県")

        # Act
        result = await use_case.create_governing_body(input_dto)

        # Assert
        assert result.success is False
        assert "Database error" in result.error_message

    @pytest.mark.asyncio
    async def test_update_governing_body_success(
        self, use_case, mock_governing_body_repository
    ):
        """Test updating a governing body successfully."""
        # Arrange
        existing_body = GoverningBody(id=1, name="東京都", type="都道府県")
        mock_governing_body_repository.get_by_id.return_value = existing_body
        # Mock get_by_name_and_type to return the same entity (no duplicate)
        mock_governing_body_repository.get_by_name_and_type.return_value = existing_body

        input_dto = UpdateGoverningBodyInputDto(
            id=1,
            name="東京都",
            type="都道府県",
            organization_code="130001",
            organization_type="prefecture",
        )

        # Act
        result = await use_case.update_governing_body(input_dto)

        # Assert
        assert isinstance(result, UpdateGoverningBodyOutputDto)
        assert result.success is True
        mock_governing_body_repository.update.assert_called_once()

    @pytest.mark.asyncio
    async def test_update_governing_body_not_found(
        self, use_case, mock_governing_body_repository
    ):
        """Test updating a governing body that does not exist."""
        # Arrange
        mock_governing_body_repository.get_by_id.return_value = None

        input_dto = UpdateGoverningBodyInputDto(
            id=999, name="存在しない", type="都道府県"
        )

        # Act
        result = await use_case.update_governing_body(input_dto)

        # Assert
        assert result.success is False
        assert "見つかりません" in result.error_message
        mock_governing_body_repository.update.assert_not_called()

    @pytest.mark.asyncio
    async def test_update_governing_body_repository_error(
        self, use_case, mock_governing_body_repository
    ):
        """Test updating a governing body with repository error."""
        # Arrange
        existing_body = GoverningBody(id=1, name="東京都", type="都道府県")
        mock_governing_body_repository.get_by_id.return_value = existing_body
        mock_governing_body_repository.get_by_name_and_type.return_value = existing_body
        mock_governing_body_repository.update.side_effect = Exception("Database error")

        input_dto = UpdateGoverningBodyInputDto(id=1, name="東京都", type="都道府県")

        # Act
        result = await use_case.update_governing_body(input_dto)

        # Assert
        assert result.success is False
        assert "Database error" in result.error_message

    @pytest.mark.asyncio
    async def test_delete_governing_body_success(
        self, use_case, mock_governing_body_repository
    ):
        """Test deleting a governing body successfully."""
        # Arrange
        existing_body = GoverningBody(id=1, name="東京都", type="都道府県")
        existing_body.conference_count = 0
        mock_governing_body_repository.get_by_id.return_value = existing_body

        input_dto = DeleteGoverningBodyInputDto(id=1)

        # Act
        result = await use_case.delete_governing_body(input_dto)

        # Assert
        assert isinstance(result, DeleteGoverningBodyOutputDto)
        assert result.success is True
        mock_governing_body_repository.delete.assert_called_once_with(1)

    @pytest.mark.asyncio
    async def test_delete_governing_body_not_found(
        self, use_case, mock_governing_body_repository
    ):
        """Test deleting a governing body that does not exist."""
        # Arrange
        mock_governing_body_repository.get_by_id.return_value = None

        input_dto = DeleteGoverningBodyInputDto(id=999)

        # Act
        result = await use_case.delete_governing_body(input_dto)

        # Assert
        assert result.success is False
        assert "見つかりません" in result.error_message
        mock_governing_body_repository.delete.assert_not_called()

    @pytest.mark.asyncio
    async def test_delete_governing_body_with_conferences(
        self, use_case, mock_governing_body_repository
    ):
        """Test deleting a governing body with associated conferences."""
        # Arrange
        existing_body = GoverningBody(id=1, name="東京都", type="都道府県")
        existing_body.conference_count = 5
        mock_governing_body_repository.get_by_id.return_value = existing_body

        input_dto = DeleteGoverningBodyInputDto(id=1)

        # Act
        result = await use_case.delete_governing_body(input_dto)

        # Assert
        assert result.success is False
        assert "会議体が関連付けられています" in result.error_message
        mock_governing_body_repository.delete.assert_not_called()

    @pytest.mark.asyncio
    async def test_delete_governing_body_repository_error(
        self, use_case, mock_governing_body_repository
    ):
        """Test deleting a governing body with repository error."""
        # Arrange
        existing_body = GoverningBody(id=1, name="東京都", type="都道府県")
        existing_body.conference_count = 0
        mock_governing_body_repository.get_by_id.return_value = existing_body
        mock_governing_body_repository.delete.side_effect = Exception("Database error")

        input_dto = DeleteGoverningBodyInputDto(id=1)

        # Act
        result = await use_case.delete_governing_body(input_dto)

        # Assert
        assert result.success is False
        assert "Database error" in result.error_message

    @pytest.mark.asyncio
    async def test_create_governing_body_with_prefecture(
        self, use_case, mock_governing_body_repository
    ):
        """Test creating a governing body with prefecture."""
        # Arrange
        mock_governing_body_repository.get_by_name_and_type.return_value = None
        created_body = GoverningBody(
            id=1,
            name="東京都",
            type="都道府県",
            prefecture="東京都",
        )
        mock_governing_body_repository.create.return_value = created_body

        input_dto = CreateGoverningBodyInputDto(
            name="東京都",
            type="都道府県",
            prefecture="東京都",
        )

        # Act
        result = await use_case.create_governing_body(input_dto)

        # Assert
        assert result.success is True
        call_args = mock_governing_body_repository.create.call_args
        assert call_args[0][0].prefecture == "東京都"

    @pytest.mark.asyncio
    async def test_update_governing_body_prefecture(
        self, use_case, mock_governing_body_repository
    ):
        """Test updating governing body prefecture."""
        # Arrange
        existing_body = GoverningBody(id=1, name="東京都", type="都道府県")
        mock_governing_body_repository.get_by_id.return_value = existing_body
        mock_governing_body_repository.get_by_name_and_type.return_value = existing_body

        input_dto = UpdateGoverningBodyInputDto(
            id=1,
            name="東京都",
            type="都道府県",
            prefecture="東京都",
        )

        # Act
        result = await use_case.update_governing_body(input_dto)

        # Assert
        assert result.success is True
        call_args = mock_governing_body_repository.update.call_args
        assert call_args[0][0].prefecture == "東京都"
