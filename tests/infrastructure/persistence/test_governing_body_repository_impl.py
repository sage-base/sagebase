"""Tests for GoverningBodyRepositoryImpl."""

from unittest.mock import AsyncMock, MagicMock

import pytest

from sqlalchemy.ext.asyncio import AsyncSession

from src.domain.entities.governing_body import GoverningBody
from src.infrastructure.persistence.governing_body_repository_impl import (
    GoverningBodyModel,
    GoverningBodyRepositoryImpl,
)


class TestGoverningBodyRepositoryImpl:
    """Test cases for GoverningBodyRepositoryImpl."""

    @pytest.fixture
    def mock_session(self) -> MagicMock:
        """Create mock async session."""
        session = MagicMock(spec=AsyncSession)
        session.execute = AsyncMock()
        session.commit = AsyncMock()
        session.rollback = AsyncMock()
        return session

    @pytest.fixture
    def repository(self, mock_session: MagicMock) -> GoverningBodyRepositoryImpl:
        """Create governing body repository."""
        return GoverningBodyRepositoryImpl(mock_session)

    @pytest.fixture
    def sample_body_entity(self) -> GoverningBody:
        """Sample governing body entity."""
        return GoverningBody(
            id=1,
            name="東京都",
            type="都道府県",
            organization_code="130001",
        )

    @pytest.mark.asyncio
    async def test_get_by_name_and_type_found(
        self,
        repository: GoverningBodyRepositoryImpl,
        mock_session: MagicMock,
    ) -> None:
        """Test get_by_name_and_type when body is found."""
        mock_row = MagicMock()
        mock_row.id = 1
        mock_row.name = "東京都"
        mock_row.type = "都道府県"
        mock_row.organization_code = "130001"

        mock_result = MagicMock()
        mock_result.fetchone = MagicMock(return_value=mock_row)
        mock_session.execute.return_value = mock_result

        result = await repository.get_by_name_and_type("東京都", "都道府県")

        assert result is not None
        assert result.id == 1
        assert result.name == "東京都"
        mock_session.execute.assert_called_once()

    @pytest.mark.asyncio
    async def test_get_by_name_and_type_not_found(
        self,
        repository: GoverningBodyRepositoryImpl,
        mock_session: MagicMock,
    ) -> None:
        """Test get_by_name_and_type when body is not found."""
        mock_result = MagicMock()
        mock_result.fetchone = MagicMock(return_value=None)
        mock_session.execute.return_value = mock_result

        result = await repository.get_by_name_and_type("存在しない", "都道府県")

        assert result is None
        mock_session.execute.assert_called_once()

    @pytest.mark.asyncio
    async def test_get_by_organization_code_found(
        self,
        repository: GoverningBodyRepositoryImpl,
        mock_session: MagicMock,
    ) -> None:
        """Test get_by_organization_code when body is found."""
        mock_row = MagicMock()
        mock_row.id = 1
        mock_row.name = "東京都"
        mock_row.type = "都道府県"
        mock_row.organization_code = "130001"

        mock_result = MagicMock()
        mock_result.fetchone = MagicMock(return_value=mock_row)
        mock_session.execute.return_value = mock_result

        result = await repository.get_by_organization_code("130001")

        assert result is not None
        assert result.organization_code == "130001"
        mock_session.execute.assert_called_once()

    @pytest.mark.asyncio
    async def test_search_by_name(
        self,
        repository: GoverningBodyRepositoryImpl,
        mock_session: MagicMock,
    ) -> None:
        """Test search_by_name with pattern matching."""
        mock_row = MagicMock()
        mock_row.id = 1
        mock_row.name = "東京都"
        mock_row.type = "都道府県"

        mock_result = MagicMock()
        mock_result.fetchall = MagicMock(return_value=[mock_row])
        mock_session.execute.return_value = mock_result

        result = await repository.search_by_name("東京")

        assert len(result) == 1
        assert result[0].name == "東京都"
        mock_session.execute.assert_called_once()

    @pytest.mark.asyncio
    async def test_count_with_conferences(
        self,
        repository: GoverningBodyRepositoryImpl,
        mock_session: MagicMock,
    ) -> None:
        """Test count_with_conferences returns count."""
        mock_result = MagicMock()
        mock_result.scalar = MagicMock(return_value=10)
        mock_session.execute.return_value = mock_result

        result = await repository.count_with_conferences()

        assert result == 10
        mock_session.execute.assert_called_once()

    @pytest.mark.asyncio
    async def test_count_with_meetings(
        self,
        repository: GoverningBodyRepositoryImpl,
        mock_session: MagicMock,
    ) -> None:
        """Test count_with_meetings returns count."""
        mock_result = MagicMock()
        mock_result.scalar = MagicMock(return_value=5)
        mock_session.execute.return_value = mock_result

        result = await repository.count_with_meetings()

        assert result == 5
        mock_session.execute.assert_called_once()

    @pytest.mark.asyncio
    async def test_count(
        self,
        repository: GoverningBodyRepositoryImpl,
        mock_session: MagicMock,
    ) -> None:
        """Test count returns total number."""
        mock_result = MagicMock()
        mock_result.scalar = MagicMock(return_value=100)
        mock_session.execute.return_value = mock_result

        result = await repository.count()

        assert result == 100
        mock_session.execute.assert_called_once()

    def test_to_entity(self, repository: GoverningBodyRepositoryImpl) -> None:
        """Test _to_entity converts model to entity correctly."""
        model = GoverningBodyModel(
            id=1,
            name="東京都",
            type="都道府県",
            organization_code="130001",
        )

        entity = repository._to_entity(model)

        assert isinstance(entity, GoverningBody)
        assert entity.id == 1
        assert entity.name == "東京都"

    def test_to_model(
        self,
        repository: GoverningBodyRepositoryImpl,
        sample_body_entity: GoverningBody,
    ) -> None:
        """Test _to_model converts entity to model correctly."""
        model = repository._to_model(sample_body_entity)

        assert isinstance(model, GoverningBodyModel)
        assert model.name == "東京都"
        assert model.type == "都道府県"
