"""ManageElectionsUseCaseのテスト."""

from unittest.mock import AsyncMock, MagicMock

import pytest

from src.application.dtos.election_dto import GenerateSeedFileOutputDto
from src.application.usecases.manage_elections_usecase import ManageElectionsUseCase
from src.domain.services.interfaces.seed_generator_service import SeedFileResult


class TestGenerateSeedFile:
    """generate_seed_fileメソッドのテスト."""

    @pytest.fixture
    def mock_election_repository(self):
        return AsyncMock()

    @pytest.fixture
    def mock_seed_generator_service(self):
        service = MagicMock()
        service.generate_and_save_elections_seed.return_value = SeedFileResult(
            content="INSERT INTO elections (id) VALUES (1);",
            file_path="database/seed_elections_generated.sql",
        )
        return service

    @pytest.fixture
    def use_case(self, mock_election_repository, mock_seed_generator_service):
        return ManageElectionsUseCase(
            election_repository=mock_election_repository,
            seed_generator_service=mock_seed_generator_service,
        )

    @pytest.mark.asyncio
    async def test_generate_seed_file_success(
        self, use_case, mock_seed_generator_service
    ):
        result = await use_case.generate_seed_file()

        assert isinstance(result, GenerateSeedFileOutputDto)
        assert result.success is True
        assert result.seed_content == "INSERT INTO elections (id) VALUES (1);"
        assert result.file_path == "database/seed_elections_generated.sql"
        mock_seed_generator_service.generate_and_save_elections_seed.assert_called_once()

    @pytest.mark.asyncio
    async def test_generate_seed_file_error(
        self, use_case, mock_seed_generator_service
    ):
        mock_seed_generator_service.generate_and_save_elections_seed.side_effect = (
            RuntimeError("DB connection failed")
        )

        result = await use_case.generate_seed_file()

        assert isinstance(result, GenerateSeedFileOutputDto)
        assert result.success is False
        assert "DB connection failed" in (result.error_message or "")

    @pytest.mark.asyncio
    async def test_generate_seed_file_without_service(self, mock_election_repository):
        use_case = ManageElectionsUseCase(
            election_repository=mock_election_repository,
        )

        result = await use_case.generate_seed_file()

        assert result.success is False
        assert "設定されていません" in (result.error_message or "")

    @pytest.mark.asyncio
    async def test_generate_seed_file_write_error(
        self, use_case, mock_seed_generator_service
    ):
        mock_seed_generator_service.generate_and_save_elections_seed.side_effect = (
            OSError("Permission denied")
        )

        result = await use_case.generate_seed_file()

        assert isinstance(result, GenerateSeedFileOutputDto)
        assert result.success is False
        assert "Permission denied" in (result.error_message or "")
